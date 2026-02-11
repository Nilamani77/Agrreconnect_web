from flask_mysqldb import MySQL, MySQLdb
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_dance.contrib.google import make_google_blueprint, google
from flask_dance.contrib.linkedin import make_linkedin_blueprint, linkedin
from flask_dance.contrib.github import make_github_blueprint, github
from flask_dance.contrib.facebook import make_facebook_blueprint, facebook
from flask_mysqldb import MySQL
from flask_bcrypt import Bcrypt
from functools import wraps
import os
import MySQLdb.cursors
from werkzeug.utils import secure_filename
from MySQLdb.cursors import DictCursor
from flask_mail import Mail, Message
from flask import jsonify
import random
from dotenv import load_dotenv
from datetime import datetime, date

comments = []
shares = []
news_list = []
now = datetime.now()
today = date.today()
news_posts = []

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

load_dotenv()

app = Flask(__name__)
app.secret_key = "supersecretkey"

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = "YOUR-MAIL"  # use your email
# use your mail app password
app.config['MAIL_PASSWORD'] = "YOUR-MAIL-APP-PASSWORD"
mail = Mail(app)


app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = "YOUR-DB-PASSWORD"  # use your db password
app.config["MYSQL_DB"] = "login_system"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"
app.config["MYSQL_CONNECT_TIMEOUT"] = 60
app.config["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

mysql = MySQL(app)
bcrypt = Bcrypt(app)


app.config["UPLOAD_FOLDER"] = "static/uploads"
app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}


google_bp = make_google_blueprint(
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    scope=[
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
        "openid"
    ],
    redirect_to="google_login"
)

app.register_blueprint(google_bp, url_prefix="/login")


@app.route("/google_login")
def google_login():
    if not google.authorized:
        return redirect(url_for("google.login"))

    resp = google.get("/oauth2/v2/userinfo")
    if resp.ok:
        info = resp.json()
        email = info.get("email")
        name = info.get("name", "Google User")

        session["user"] = name
        session["user_email"] = email

        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        existing = cursor.fetchone()
        if not existing:
            cursor.execute("INSERT INTO users (name, email, password) VALUES (%s,%s,%s)",
                           (name, email, ""))
            mysql.connection.commit()
        cursor.close()

        flash("Logged in with Google!", "success")
        return redirect(url_for("project"))
    flash("Google login failed.", "danger")
    return redirect(url_for("home", show="signin"))


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def allowed_file(fname: str) -> bool:
    return "." in fname and fname.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for("home", show="signin"))
        return f(*args, **kwargs)
    return wrapper


def farmer_login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "farmer_email" not in session:
            flash("Please log in as a farmer first.", "warning")
            return redirect(url_for("farmer_login"))
        return f(*args, **kwargs)
    return wrapper


@app.route("/")
def home():
    show = request.args.get("show", "signin")
    return render_template("login.html", show=show)


@app.route("/signup", methods=["POST"])
def signup():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    if not name or not email or not password:
        flash("All fields are required.", "danger")
        return redirect(url_for("home", show="signup"))

    cur = mysql.connection.cursor()
    try:
        hashed = bcrypt.generate_password_hash(password).decode("utf-8")
        cur.execute("INSERT INTO users (name, email, password) VALUES (%s,%s,%s)",
                    (name, email, hashed))
        mysql.connection.commit()
        flash("Signup successful! Please sign in.", "success")
        return redirect(url_for("home", show="signin"))
    except Exception as e:
        print("Signup error:", e)
        mysql.connection.rollback()
        flash("Email already exists or error occurred.", "danger")
        return redirect(url_for("home", show="signup"))
    finally:
        cur.close()


@app.route("/signin", methods=["POST"])
def signin():
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    cur = mysql.connection.cursor()
    try:
        cur.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cur.fetchone()
    finally:
        cur.close()

    if user and bcrypt.check_password_hash(user["password"], password):
        session["user"] = user["name"]
        session["user_email"] = user["email"]
        return redirect(url_for("project"))
    flash("Invalid email or password.", "danger")
    return redirect(url_for("home", show="signin"))


@app.route("/logout")
def logout():
    session.pop("user", None)
    session.pop("user_email", None)
    flash("Logged out.", "info")
    return redirect(url_for("home", show="signin"))


@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email").strip().lower()
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cur.fetchone()
        cur.close()

        if not user:
            flash("Email not registered.", "danger")
            return redirect(url_for("forgot_password"))

        otp = str(random.randint(100000, 999999))
        session["reset_email"] = email
        session["reset_otp"] = otp

        msg = Message("Password Reset OTP",
                      sender="your_email@gmail.com", recipients=[email])
        msg.body = f"Your OTP for password reset is {otp}. It will expire in 5 minutes."
        mail.send(msg)

        flash("OTP sent to your email.", "info")
        return redirect(url_for("verify_otp"))

    return render_template("forgot_password.html")


@app.route("/verify_otp", methods=["GET", "POST"])
def verify_otp():
    if request.method == "POST":
        otp = request.form.get("otp")
        if otp == session.get("reset_otp"):
            flash("OTP verified. Enter new password.", "success")
            return redirect(url_for("reset_password"))
        else:
            flash("Invalid OTP. Try again.", "danger")
            return redirect(url_for("verify_otp"))

    return render_template("verify_otp.html")


@app.route("/reset_password", methods=["GET", "POST"])
def reset_password():
    if request.method == "POST":
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")

        if new_password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("reset_password"))

        email = session.get("reset_email")
        if not email:
            flash("Session expired. Try again.", "danger")
            return redirect(url_for("forgot_password"))

        hashed = bcrypt.generate_password_hash(new_password).decode("utf-8")
        cur = mysql.connection.cursor()
        cur.execute("UPDATE users SET password=%s WHERE email=%s",
                    (hashed, email))
        mysql.connection.commit()
        cur.close()

        session.pop("reset_email", None)
        session.pop("reset_otp", None)

        flash("Password reset successful! Please log in.", "success")
        return redirect(url_for("home", show="signin"))

    return render_template("reset_password.html")


@app.route("/farmers")
def farmers():
    return render_template("farm.html")


@app.route("/project")
def project():
    """Main project page route - fetches reviews and products for display"""
    all_reviews = []
    all_products = []

    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # Fetch reviews
        cursor.execute("""
            SELECT 
                id, name, photo, review_text, rating, created_at 
            FROM reviews 
            ORDER BY created_at DESC
        """)
        all_reviews = cursor.fetchall()

        # Fetch products + ratings + farmer details
        cursor.execute("""
            SELECT 
                p.id, 
                p.name, 
                p.price, 
                p.qty, 
                p.image, 
                f.farmer_name, 
                f.shop_name,
                COALESCE(AVG(r.rating), 0) AS avg_rating,
                COUNT(r.rating) AS total_ratings
            FROM products p
            LEFT JOIN farmers f ON p.farmer_email = f.email
            LEFT JOIN ratings r ON p.id = r.product_id
            GROUP BY p.id
            ORDER BY p.id DESC
        """)
        all_products = cursor.fetchall()

        cursor.close()

        print(
            f"✅ Project route - Retrieved {len(all_reviews)} reviews and {len(all_products)} products from database"
        )

    except Exception as e:
        print("❌ PROJECT ROUTE FETCH ERROR ❌")
        print("Error:", e)

    return render_template("project.html", reviews=all_reviews, products=all_products)


@app.route("/welcome")
def welcome():
    if "user" in session:
        return render_template("welcome.html", username=session["user"])
    return redirect(url_for("home", show="signin"))


@app.route("/search")
def search():
    query = request.args.get("query", "").strip()

    if not query:
        return redirect(url_for("products"))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""
        SELECT * FROM products
        WHERE name LIKE %s
    """, (f"%{query}%",))
    products = cursor.fetchall()
    cursor.close()

    return render_template("product.html", products=products, search_query=query)


@app.route("/farmer/login", methods=["GET", "POST"])
def farmer_login():
    print("Accessing /farmer/login")
    if "farmer_email" in session:
        flash("You are already logged in.", "info")
        return redirect(url_for("farmer_dashboard"))

    if request.method == "POST":
        raw_email = request.form.get("email")
        email = raw_email.strip().lower()
        print(f"Raw email received: '{raw_email}'")
        print(f"Processed email: '{email}'")
        password = request.form.get("password")

        cursor = mysql.connection.cursor()
        try:
            cursor.execute("SELECT * FROM farmers WHERE email = %s", (email,))
            farmer = cursor.fetchone()
        finally:
            cursor.close()

        if farmer and bcrypt.check_password_hash(farmer["password"], password):
            session["farmer_email"] = farmer["email"].lower()
            session["farmer_name"] = farmer["farmer_name"]
            flash("Farmer logged in successfully!", "success")
            return redirect(url_for("farmer_dashboard"))
        else:
            flash("Invalid email or password.", "danger")

    return render_template("farmer_login.html")


@app.route("/farmer/register", methods=["GET", "POST"])
def farmer_register():
    if "farmer_email" in session:
        flash("You are already logged in.", "info")
        return redirect(url_for("farmer_dashboard"))

    if request.method == "POST":
        farmer_name = request.form.get("farmer_name")
        shop_name = request.form.get("shop_name")
        contact = request.form.get("contact")
        email = request.form.get("email").strip().lower()
        address = request.form.get("address")
        password = request.form.get("password")

        if not (farmer_name and shop_name and email and password):
            flash("All fields are required.", "danger")
            return redirect(url_for("farmer_register"))

        hashed_password = bcrypt.generate_password_hash(
            password).decode("utf-8")

        cursor = mysql.connection.cursor()
        try:
            cursor.execute(
                "INSERT INTO farmers (farmer_name, shop_name, contact, email, address, password) "
                "VALUES (%s,%s,%s,%s,%s,%s)",
                (farmer_name, shop_name, contact, email, address, hashed_password)
            )
            mysql.connection.commit()
            flash("Shop registered successfully! Please log in.", "success")
            return redirect(url_for("farmer_login"))
        except Exception as e:
            print("Register shop error:", e)
            mysql.connection.rollback()
            flash("Error registering shop. Maybe email already exists.", "danger")
            return redirect(url_for("farmer_register"))
        finally:
            cursor.close()

    return render_template("farm.html")


@app.route("/farmer/dashboard")
@farmer_login_required
def farmer_dashboard():
    cursor = mysql.connection.cursor()
    try:

        cursor.execute(
            "SELECT * FROM products WHERE farmer_email = %s", (session["farmer_email"],))
        products = cursor.fetchall()

        #
        cursor.execute(
            """SELECT SUM(o.qty * p.price) as total_sales
               FROM orders o
               JOIN products p ON o.product_id = p.id
               WHERE p.farmer_email = %s""",
            (session["farmer_email"],)
        )
        row = cursor.fetchone()
        total_sales = row["total_sales"] or 0
    finally:
        cursor.close()

    return render_template("farmer_dashboard.html",
                           products=products,
                           total_sales=total_sales,
                           farmer_name=session.get("farmer_name"))


@app.route("/farmer/logout")
def farmer_logout():
    session.pop("farmer_email", None)
    session.pop("farmer_name", None)
    flash("Farmer logged out.", "info")
    return redirect(url_for("farmer_login"))


@app.route("/farmer/add_product", methods=["POST"])
@farmer_login_required
def add_product():
    name = request.form.get("name")
    price = float(request.form.get("price", 0))
    qty = int(request.form.get("qty", 0))

    category = request.form["category"].strip().lower()

    category_map = {
        'fruits': 'fruit',
        'veg': 'vegetable',
        'vegetables': 'vegetable',
        'dairy': 'dairy',

    }

    category = category_map.get(category, category)

    file = request.files.get("image")

    if not name or not category:
        flash("Product name and category are required.", "danger")
        return redirect(url_for("farmer_dashboard"))

    allowed_categories = {'vegetable', 'fruit', 'dairy'}
    if category not in allowed_categories:
        flash("Invalid category selected.", "danger")
        return redirect(url_for("farmer_dashboard"))

    if not category or category not in allowed_categories:
        flash("Invalid category selected.", "danger")
        return redirect(url_for("farmer_dashboard"))

    image_filename = None
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        image_filename = filename
        file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

    cursor = mysql.connection.cursor()
    try:
        cursor.execute(
            "INSERT INTO products (farmer_email, name, price, qty, image, category) VALUES (%s, %s, %s, %s, %s, %s)",
            (session["farmer_email"], name, price, qty,
             image_filename, category)
        )
        mysql.connection.commit()
        flash("Product Added Successfully!", "success")
    except Exception as e:
        print("Add product error:", e)
        mysql.connection.rollback()
        flash("Could not add product.", "danger")
    finally:
        cursor.close()

    if category == "vegetable":
        return redirect(url_for("vegetables"))
    elif category == "fruit":
        return redirect(url_for("fruits"))
    elif category == "dairy":
        return redirect(url_for("dairy"))
    else:
        return redirect(url_for("products"))


@app.route("/farmer/delete_product/<int:id>", methods=["POST", "GET"])
@farmer_login_required
def delete_product(id):
    cursor = mysql.connection.cursor()
    try:
        cursor.execute("DELETE FROM products WHERE id = %s AND farmer_email = %s",
                       (id, session["farmer_email"]))
        mysql.connection.commit()
        flash("Product Deleted!", "danger")
    except Exception as e:
        print("Delete product error:", e)
        mysql.connection.rollback()
        flash("Could not delete product.", "danger")
    finally:
        cursor.close()

    return redirect(url_for("farmer_dashboard"))


@app.route("/farmer/update_price/<int:id>", methods=["POST"])
@farmer_login_required
def update_price(id):
    new_price = request.form.get("price")
    try:
        new_price = float(new_price)
    except (ValueError, TypeError):
        flash("Invalid price entered.", "danger")
        return redirect(url_for("farmer_dashboard"))

    cursor = mysql.connection.cursor()
    try:
        cursor.execute(
            "UPDATE products SET price = %s WHERE id = %s AND farmer_email = %s",
            (new_price, id, session["farmer_email"])
        )
        mysql.connection.commit()
        flash("Price updated successfully!", "success")
    except Exception as e:
        print("Update price error:", e)
        mysql.connection.rollback()
        flash("Could not update price.", "danger")
    finally:
        cursor.close()

    return redirect(url_for("farmer_dashboard"))


@app.route("/farmer/add_news", methods=["POST"])
@farmer_login_required
def add_news():
    title = request.form.get("title")
    content = request.form.get("content")
    file = request.files.get("image")

    if not title or not content:
        flash("Title and Content are required.", "danger")
        return redirect(url_for("farmer_dashboard"))

    image_filename = None
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        image_filename = filename
        file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

    cursor = mysql.connection.cursor()
    try:
        cursor.execute(
            "INSERT INTO news (farmer_email, title, content, image) VALUES (%s, %s, %s, %s)",
            (session["farmer_email"], title, content, image_filename)
        )
        mysql.connection.commit()
        flash("News posted successfully!", "success")
    except Exception as e:
        print("Add news error:", e)
        mysql.connection.rollback()
        flash("Could not post news.", "danger")
    finally:
        cursor.close()

    return redirect(url_for("farmer_dashboard"))


@app.route("/news", methods=["GET", "POST"])
def news():
    cursor = mysql.connection.cursor(
        MySQLdb.cursors.DictCursor)

    message = None
    if request.method == "POST":
        email = request.form.get("email")
        message = "✅ Thank you for subscribing!"

    cursor.execute("SELECT * FROM news ORDER BY created_at DESC")
    all_news = cursor.fetchall()

    cursor.execute("SELECT * FROM comments ORDER BY created_at ASC")
    all_comments = cursor.fetchall()
    cursor.close()

    comments_by_news = {}
    for c in all_comments:
        comments_by_news.setdefault(c['news_id'], []).append(c)

    for post in all_news:
        post['comments'] = comments_by_news.get(post['id'], [])

    return render_template(
        "news.html",
        news=all_news,
        is_subscriber=True,
        is_farmer="farmer_email" in session,
        message=message
    )


@app.route("/like/<int:news_id>", methods=["POST"])
def like_news(news_id):
    cursor = mysql.connection.cursor()
    try:

        cursor.execute(
            "UPDATE news SET like_count = IFNULL(like_count, 0) + 1 WHERE id = %s", (news_id,))
        mysql.connection.commit()
    except Exception as e:
        print("Like error:", e)
        mysql.connection.rollback()
    finally:
        cursor.close()

    return redirect(url_for("news"))


@app.route('/add_comment/<int:news_id>', methods=['POST'])
def add_comment(news_id):
    comment_text = request.form.get('comment', '').strip()
    user_email = session.get("user_email", "anonymous@example.com")

    if not comment_text:
        flash("Comment cannot be empty.", "warning")
    else:
        cursor = mysql.connection.cursor()
        cursor.execute("""
            INSERT INTO comments (news_id, user, comment, created_at)
            VALUES (%s, %s, %s, NOW())
        """, (news_id, user_email, comment_text))
        mysql.connection.commit()
        cursor.close()
        flash("Comment added successfully!", "success")

    return redirect(url_for("news"))


@app.route('/share_news/<int:news_id>', methods=['POST'])
def share_news(news_id):
    user_email = "anonymous@example.com"

    shares.append({
        'news_id': news_id,
        'shared_by': user_email,
        'created_at': datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    })

    flash("News shared successfully!", "success")
    return redirect(url_for('news'))


@app.route("/products")
def products():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    try:
        # Query to get products with average rating and total ratings
        query = """
        SELECT 
            p.*, 
            f.shop_name, 
            f.farmer_name,
            COALESCE(AVG(r.rating), 0) as avg_rating,
            COUNT(r.rating) as total_ratings
        FROM products p 
        LEFT JOIN farmers f ON p.farmer_email = f.email
        LEFT JOIN ratings r ON p.id = r.product_id
        GROUP BY p.id
        """
        cursor.execute(query)
        all_products = cursor.fetchall()
    finally:
        cursor.close()

    return render_template("product.html", products=all_products)


@app.route('/rate-product', methods=['POST'])
def rate_product():
    try:
        data = request.get_json()
        product_id = data.get('product_id')
        rating = data.get('rating')
        user_email = session.get('user_email')

        print(f"=== RATING DEBUG ===")
        print(f"User Email: {user_email}")
        print(f"Product ID: {product_id}")
        print(f"Rating: {rating}")
        print(f"Session keys: {list(session.keys())}")
        print(f"===================")

        if not user_email:
            return jsonify({'success': False, 'message': 'Login required'}), 401

        if not product_id or not rating:
            return jsonify({'success': False, 'message': 'Missing data'}), 400

        # Validate rating is between 1-5
        if rating < 1 or rating > 5:
            return jsonify({'success': False, 'message': 'Rating must be between 1 and 5'}), 400

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        cursor.execute(
            "SELECT id FROM ratings WHERE user_email = %s AND product_id = %s",
            (user_email, product_id)
        )
        existing_rating = cursor.fetchone()
        print(f"Existing rating: {existing_rating}")

        if existing_rating:
            # Update existing rating
            cursor.execute(
                "UPDATE ratings SET rating = %s WHERE user_email = %s AND product_id = %s",
                (rating, user_email, product_id)
            )
            print("Updated existing rating")
        else:
            # Create new rating (using email instead of user_id)
            cursor.execute(
                "INSERT INTO ratings (user_email, product_id, rating) VALUES (%s, %s, %s)",
                (user_email, product_id, rating)
            )
            print("Inserted new rating")

        mysql.connection.commit()

        cursor.execute(
            "SELECT * FROM ratings WHERE user_email = %s AND product_id = %s",
            (user_email, product_id)
        )
        saved_rating = cursor.fetchone()
        cursor.close()
        print(f"Saved rating in DB: {saved_rating}")

        if saved_rating:
            return jsonify({'success': True, 'message': 'Rating saved successfully!'})
        else:
            return jsonify({'success': False, 'message': 'Failed to save rating'}), 500

    except Exception as e:
        print(f"Error in rating route: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route("/products/vegetable")
def vegetables():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    try:
        cursor.execute("""
            SELECT 
                p.*, 
                f.shop_name, 
                f.farmer_name,
                COALESCE(AVG(r.rating), 0) AS avg_rating,
                COUNT(r.rating) AS total_ratings
            FROM products p
            LEFT JOIN farmers f ON p.farmer_email = f.email
            LEFT JOIN ratings r ON p.id = r.product_id
            WHERE LOWER(TRIM(p.category)) = 'vegetable'
            GROUP BY p.id
        """)
        items = cursor.fetchall()
    except Exception as e:
        print("ERROR in vegetables:", e)
        items = []
    finally:
        cursor.close()
    return render_template("veg.html", products=items)


@app.route("/products/fruit")
def fruits():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    try:
        cursor.execute("""
            SELECT 
                p.*, 
                f.shop_name, 
                f.farmer_name,
                COALESCE(AVG(r.rating), 0) AS avg_rating,
                COUNT(r.rating) AS total_ratings
            FROM products p
            LEFT JOIN farmers f ON p.farmer_email = f.email
            LEFT JOIN ratings r ON p.id = r.product_id
            WHERE LOWER(TRIM(p.category)) = 'fruit'
            GROUP BY p.id
        """)
        items = cursor.fetchall()
    except Exception as e:
        print("ERROR in fruits:", e)
        items = []
    finally:
        cursor.close()
    return render_template("fruit.html", products=items)


@app.route("/products/dairy")
def dairy():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    try:
        cursor.execute("""
            SELECT 
                p.*, 
                f.shop_name, 
                f.farmer_name,
                COALESCE(AVG(r.rating), 0) AS avg_rating,
                COUNT(r.rating) AS total_ratings
            FROM products p
            LEFT JOIN farmers f ON p.farmer_email = f.email
            LEFT JOIN ratings r ON p.id = r.product_id
            WHERE LOWER(TRIM(p.category)) = 'dairy'
            GROUP BY p.id
        """)
        items = cursor.fetchall()
    except Exception as e:
        print("ERROR in dairy_page:", e)
        items = []
    finally:
        cursor.close()
    return render_template("dairy.html", products=items)


def get_cart_from_db():
    if "user_email" not in session:
        return []
    email = session["user_email"]
    cursor = mysql.connection.cursor()
    cursor.execute(
        "SELECT c.product_id, c.quantity, p.name, p.price, p.image "
        "FROM cart c JOIN products p ON c.product_id = p.id "
        "WHERE c.user_email = %s", (email,)
    )
    items = cursor.fetchall()
    cursor.close()
    return items


def add_to_cart_db(product_id, quantity=1):
    if "user_email" not in session:
        return False
    email = session["user_email"]
    cursor = mysql.connection.cursor()

    cursor.execute(
        "SELECT quantity FROM cart WHERE user_email = %s AND product_id = %s",
        (email, product_id)
    )
    row = cursor.fetchone()

    if row:
        new_qty = row["quantity"] + quantity
        cursor.execute(
            "UPDATE cart SET quantity = %s WHERE user_email = %s AND product_id = %s",
            (new_qty, email, product_id)
        )
    else:
        cursor.execute(
            "INSERT INTO cart (user_email, product_id, quantity) VALUES (%s, %s, %s)",
            (email, product_id, quantity)
        )

    mysql.connection.commit()
    cursor.close()
    return True


def update_cart_db(product_id, action):
    if "user_email" not in session:
        return
    email = session["user_email"]
    cursor = mysql.connection.cursor()

    cursor.execute(
        "SELECT quantity FROM cart WHERE user_email = %s AND product_id = %s",
        (email, product_id)
    )
    row = cursor.fetchone()

    if not row:
        return

    qty = row["quantity"]

    if action == "increase":
        cursor.execute(
            "UPDATE cart SET quantity = quantity + 1 WHERE user_email = %s AND product_id = %s",
            (email, product_id)
        )
    elif action == "decrease":
        if qty > 1:
            cursor.execute(
                "UPDATE cart SET quantity = quantity - 1 WHERE user_email = %s AND product_id = %s",
                (email, product_id)
            )
        else:
            cursor.execute(
                "DELETE FROM cart WHERE user_email = %s AND product_id = %s",
                (email, product_id)
            )
    elif action == "delete":
        cursor.execute(
            "DELETE FROM cart WHERE user_email = %s AND product_id = %s",
            (email, product_id)
        )

    mysql.connection.commit()
    cursor.close()


@app.context_processor
def cart_processor():

    if "user_email" in session:
        cursor = mysql.connection.cursor()
        try:
            cursor.execute(
                "SELECT SUM(quantity) as total_items, SUM(p.price * c.quantity) as total_price "
                "FROM cart c JOIN products p ON c.product_id = p.id "
                "WHERE c.user_email = %s", (session["user_email"],)
            )
            result = cursor.fetchone()
            total_items = result["total_items"] or 0 if result else 0
            total_price = result["total_price"] or 0 if result else 0
        except:
            total_items = 0
            total_price = 0
        finally:
            cursor.close()
    else:
        total_items = 0
        total_price = 0

    return dict(nav_cart_count=total_items, nav_total=total_price)


@app.route("/add_to_cart/<int:product_id>", methods=["POST"])
def add_to_cart(product_id):
    if "user_email" not in session:
        flash("Please log in to add items to your cart.", "warning")
        return redirect(url_for("home", show="signin"))

    email = session["user_email"]
    cursor = mysql.connection.cursor()
    try:
        cursor.execute(
            "SELECT quantity FROM cart WHERE user_email = %s AND product_id = %s",
            (email, product_id)
        )
        existing = cursor.fetchone()

        if existing:

            new_qty = existing["quantity"] + 1
            cursor.execute(
                "UPDATE cart SET quantity = %s WHERE user_email = %s AND product_id = %s",
                (new_qty, email, product_id)
            )
            flash("Quantity updated!", "success")
        else:

            cursor.execute(
                "INSERT INTO cart (user_email, product_id, quantity) VALUES (%s, %s, %s)",
                (email, product_id, 1)
            )
            flash("Product added to cart!", "success")

        mysql.connection.commit()

    except Exception as e:
        print("Add to cart error:", e)
        mysql.connection.rollback()
        flash("Could not add product to cart.", "danger")
    finally:
        cursor.close()

    return redirect(request.referrer or url_for("products"))


@app.route("/cart")
def cart():
    if "user_email" not in session:
        flash("Please log in to view your cart.", "warning")
        return redirect(url_for("home", show="signin"))

    email = session["user_email"]
    cursor = mysql.connection.cursor()
    try:

        cursor.execute(
            "SELECT c.product_id as id, c.quantity, p.name, p.price, p.image "
            "FROM cart c JOIN products p ON c.product_id = p.id "
            "WHERE c.user_email = %s", (email,)
        )
        cart_items = cursor.fetchall()

        total = sum(float(item["price"]) * item["quantity"]
                    for item in cart_items)

        cursor.execute(
            "SELECT s.product_id as id, s.quantity, p.name, p.price, p.image "
            "FROM saved_items s JOIN products p ON s.product_id = p.id "
            "WHERE s.user_email = %s", (email,)
        )
        saved_items = cursor.fetchall()

    except Exception as e:
        print("Cart fetch error:", e)
        cart_items = []
        saved_items = []
        total = 0
    finally:
        cursor.close()

    return render_template("cart.html", cart=cart_items, saved_items=saved_items, total=total)


@app.route("/update_cart/<int:product_id>", methods=["POST"])
def update_cart(product_id):
    if "user_email" not in session:
        flash("Please log in to update your cart.", "warning")
        return redirect(url_for("home", show="signin"))

    action = request.form.get("action")
    email = session["user_email"]
    cursor = mysql.connection.cursor()

    try:
        if action == "save":

            cursor.execute(
                "SELECT quantity FROM cart WHERE user_email = %s AND product_id = %s",
                (email, product_id)
            )
            row = cursor.fetchone()

            if row:
                qty = row["quantity"]

                cursor.execute(
                    "INSERT INTO saved_items (user_email, product_id, quantity) VALUES (%s, %s, %s)",
                    (email, product_id, qty)
                )
                cursor.execute(
                    "DELETE FROM cart WHERE user_email = %s AND product_id = %s",
                    (email, product_id)
                )
                flash("Item saved for later!", "info")

        elif action == "increase":
            cursor.execute(
                "UPDATE cart SET quantity = quantity + 1 WHERE user_email = %s AND product_id = %s",
                (email, product_id)
            )
        elif action == "decrease":
            cursor.execute(
                "SELECT quantity FROM cart WHERE user_email = %s AND product_id = %s",
                (email, product_id)
            )
            row = cursor.fetchone()
            if row and row["quantity"] > 1:
                cursor.execute(
                    "UPDATE cart SET quantity = quantity - 1 WHERE user_email = %s AND product_id = %s",
                    (email, product_id)
                )
            else:
                cursor.execute(
                    "DELETE FROM cart WHERE user_email = %s AND product_id = %s",
                    (email, product_id)
                )
        elif action == "delete":
            cursor.execute(
                "DELETE FROM cart WHERE user_email = %s AND product_id = %s",
                (email, product_id)
            )

        mysql.connection.commit()

    except Exception as e:
        print("Update cart error:", e)
        mysql.connection.rollback()
        flash("Could not update cart.", "danger")
    finally:
        cursor.close()

    return redirect(url_for("cart"))


@app.route("/checkout")
def checkout():
    if "user_email" not in session:
        flash("Please log in to checkout.", "warning")
        return redirect(url_for("home", show="signin"))

    email = session["user_email"]
    cursor = mysql.connection.cursor()
    try:

        cursor.execute(
            "SELECT c.product_id as id, c.quantity, p.name, p.price, p.image "
            "FROM cart c JOIN products p ON c.product_id = p.id "
            "WHERE c.user_email = %s", (email,)
        )
        cart_items = cursor.fetchall()

        total = sum(float(item["price"]) * item["quantity"]
                    for item in cart_items)
    except Exception as e:
        print("Checkout error:", e)
        cart_items = []
        total = 0
    finally:
        cursor.close()

    return render_template("checkout.html", cart=cart_items, total=total)


@app.route("/move_to_cart/<int:product_id>", methods=["POST"])
def move_to_cart(product_id):
    if "user_email" not in session:
        flash("Please log in.", "warning")
        return redirect(url_for("home", show="signin"))

    email = session["user_email"]
    cursor = mysql.connection.cursor()

    try:

        cursor.execute(
            "SELECT quantity FROM saved_items WHERE user_email = %s AND product_id = %s",
            (email, product_id)
        )
        row = cursor.fetchone()

        if row:
            qty = row["quantity"]

            cursor.execute(
                "INSERT INTO cart (user_email, product_id, quantity) VALUES (%s, %s, %s) "
                "ON DUPLICATE KEY UPDATE quantity = quantity + %s",
                (email, product_id, qty, qty)
            )

            cursor.execute(
                "DELETE FROM saved_items WHERE user_email = %s AND product_id = %s",
                (email, product_id)
            )

            mysql.connection.commit()
            flash("Item moved back to cart!", "success")

    except Exception as e:
        print("Move to cart error:", e)
        mysql.connection.rollback()
    finally:
        cursor.close()

    return redirect(url_for("cart"))


@app.route("/reviews", methods=["GET", "POST"])
def reviews():
    print("=== REVIEWS ROUTE CALLED ===")
    print(f"Request method: {request.method}")

    if request.method == "POST":

        name = request.form.get("name")
        review_text = request.form.get("review")
        rating = request.form.get("rating")
        photo = request.files.get("photo")

        if not name or not review_text or not rating:
            flash("Name, review, and rating are required.", "danger")
            return redirect(url_for("project"))

        words = review_text.split()
        if len(words) > 100:
            review_text = " ".join(words[:100])
            flash(
                "Your review was too long. Only the first 100 words were saved.", "warning")

        filename = None
        if photo and allowed_file(photo.filename):
            filename = secure_filename(photo.filename)
            save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            try:
                photo.save(save_path)
            except Exception as e:
                print(f"Error saving photo: {e}")
                filename = None

        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "INSERT INTO reviews (name, photo, review_text, rating) VALUES (%s, %s, %s, %s)",
                (name, filename, review_text, int(rating))
            )
            mysql.connection.commit()
            cursor.close()
            flash("Thank you for your review!", "success")
        except Exception as e:
            print("Review insert error:", e)
            mysql.connection.rollback()
            flash("Could not submit review.", "danger")

        return redirect(url_for("project"))

    try:
        cursor = mysql.connection.cursor()
        cursor.execute(
            "SELECT id, name, photo, review_text, rating, created_at FROM reviews ORDER BY created_at DESC"
        )
        all_reviews = cursor.fetchall()
        cursor.close()

        print(f"Retrieved {len(all_reviews)} reviews from database")

    except Exception as e:
        print("!!! REVIEWS FETCH ERROR !!!")
        print("Error:", e)
        all_reviews = []
        flash("Could not load reviews.", "warning")

    return render_template("project.html", reviews=all_reviews)


@app.route("/place_order", methods=["POST"])
def place_order():
    if "user_email" not in session:
        return redirect(url_for("home", show="signin"))

    email = session["user_email"]
    fullname = request.form["fullname"]
    phone = request.form["phone"]
    address = request.form["address"]
    city = request.form["city"]
    state = request.form["state"]
    pincode = request.form["pincode"]
    total = request.form["total"]

    cursor = mysql.connection.cursor()

    try:
        cursor.execute("""
            INSERT INTO full_orders
            (user_email, fullname, phone, address, city, state, pincode, total_amount)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (email, fullname, phone, address, city, state, pincode, total))
        mysql.connection.commit()

        order_id = cursor.lastrowid

        cursor.execute("""
            SELECT c.product_id AS id, c.quantity, p.name, p.price
            FROM cart c 
            JOIN products p ON c.product_id = p.id
            WHERE c.user_email = %s
        """, (email,))
        cart = cursor.fetchall()

        for item in cart:
            cursor.execute("""
                INSERT INTO order_items (order_id, product_id, product_name, quantity, price, user_email)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                order_id,
                item["id"],
                item["name"],
                item["quantity"],
                item["price"],
                email
            ))

        mysql.connection.commit()

        # Clear cart
        cursor.execute("DELETE FROM cart WHERE user_email=%s", (email,))
        mysql.connection.commit()

    except Exception as e:
        print("ORDER ERROR:", e)

    finally:
        cursor.close()

    return redirect(url_for("order_summary"))


@app.route("/order_summary")
def order_summary():
    if "user_email" not in session:
        return redirect(url_for("home", show="signin"))

    email = session["user_email"]
    cursor = mysql.connection.cursor()

    cursor.execute("""
        SELECT * FROM full_orders
        WHERE user_email=%s
        ORDER BY id DESC
        LIMIT 1
    """, (email,))
    order = cursor.fetchone()

    items = []

    if order:
        cursor.execute("""
            SELECT oi.id, oi.order_id, oi.product_id, oi.product_name,
                   oi.quantity, oi.price, oi.user_email,
                   p.image AS product_image
            FROM order_items oi
            LEFT JOIN products p ON oi.product_id = p.id
            WHERE oi.order_id = %s
        """, (order['id'],))
        items = cursor.fetchall()

    cursor.close()

    return render_template("order_summary.html", order=order, items=items)


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
