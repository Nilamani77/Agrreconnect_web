# Agrreconnect_web
![Python](https://img.shields.io/badge/Python-3.10-blue)
![Flask](https://img.shields.io/badge/Flask-Framework-black)

🌾 AgriConnect – Farmer Support & Market Linkage Portal

AgriConnect is a web-based platform designed to connect farmers directly with buyers, provide market price updates, and offer agricultural support services. The system helps eliminate middlemen and improve farmer income.

This project is built using Flask (Python) for backend and HTML/CSS/JavaScript for frontend.

🚀 Features
👨‍🌾 Farmer Registration & Login
🔐 Google OAuth Login Integration
📦 Product Listing by Farmers
🛒 Buyer Product Browsing
📊 Market Price Information
📁 Secure Authentication System
🗂 Database Integration (SQLite/MySQL)
🔒 Environment-based secret protection

🛠 Tech Stack
Frontend:
HTML
CSS
JavaScript


Backend:
Python
Flask
Flask-Dance (Google OAuth)
Database:
SQLite / MySQL

📂 Project Structure
Agreconnect_web/
│
├── project.py
├── templates/
├── static/
├── .env (ignored)
├── .gitignore
└── README.md

## 📸 Screenshots

![Home Page](static/images/home.png)

⚙️ Installation Guide
1️⃣ Clone the Repository
git clone https://github.com/Nilamani77/Agrreconnect_web.git
cd Agrreconnect_web

2️⃣ Create Virtual Environment
python -m venv venv
venv\Scripts\activate   # Windows

3️⃣ Install Dependencies
pip install -r requirements.txt

4️⃣ Create .env File
Create a .env file in the root folder:
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret

▶️ Run the Application
python project.py

Open browser:
http://127.0.0.1:5000

🔐 Security
OAuth credentials stored using environment variables
.env file excluded using .gitignore
No hardcoded secrets

🎯 Future Enhancements
Payment Gateway Integration
Admin Dashboard
AI-based Crop Recommendation
Real-time Market Price API
Deployment on Cloud (AWS/Render)

👤 Author
Nilamani Kundu
B.Tech CSE (AI & ML)
GitHub: https://github.com/Nilamani77