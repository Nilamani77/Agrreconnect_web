
let shoppingCart = document.querySelector('.shopping-cart');

document.querySelector('#cart-btn').onclick = () => {
    shoppingCart.classList.toggle('active');
    navbar.classList.remove('active');
    searchForm.classList.remove('active');
    loginForm.classList.remove('active');

}

let loginForm = document.querySelector('.login-form');

document.querySelector('#login-btn').onclick = () => {
    loginForm.classList.toggle('active');
    navbar.classList.remove('active');
    searchForm.classList.remove('active');
    shoppingCart.classList.remove('active');

}
let navbar = document.querySelector('.navbar');

document.querySelector('#menu-btn').onclick = () => {
    navbar.classList.toggle('active');
    searchForm.classList.remove('active');
    shoppingCart.classList.remove('active');
    loginForm.classList.remove('active');

}
window.onscroll = () => {
    navbar.classList.remove('active');
    searchForm.classList.remove('active');
    shoppingCart.classList.remove('active');
    loginForm.classList.remove('active');

}

function toggleText() {
    const moreText = document.getElementById("moreText");
    const btn = event.target;

    if (moreText.style.display === "none") {
        moreText.style.display = "inline";
        btn.textContent = "Read Less";
    } else {
        moreText.style.display = "none";
        btn.textContent = "Read More";
    }
}

function toggletext() {
    const moreText = document.getElementById("moretext");
    const btn = event.target;

    if (moreText.style.display === "none") {
        moreText.style.display = "inline";
        btn.textContent = "Read Less";
    } else {
        moreText.style.display = "none";
        btn.textContent = "Read More";
    }
}

function toggleteXt() {
    const moreText = document.getElementById("MoreText");
    const btn = event.target;

    if (moreText.style.display === "none") {
        moreText.style.display = "inline";
        btn.textContent = "Read Less";
    } else {
        moreText.style.display = "none";
        btn.textContent = "Read More";
    }
}

// Wait for DOM to be fully loade

// Initialize Product Swiper
if (document.querySelector(".product-slider")) {
    new Swiper(".product-slider", {
        loop: true,
        spaceBetween: 20,
        autoplay: {
            delay: 3000,
            disableOnInteraction: false,
        },
        navigation: {
            nextEl: ".swiper-button-next",
            prevEl: ".swiper-button-prev",
        },
        breakpoints: {
            0: { slidesPerView: 1 },
            768: { slidesPerView: 2 },
            1024: { slidesPerView: 3 },
        },
    });
}

// Initialize Review Swiper
if (document.querySelector(".mySwiper")) {
    new Swiper(".mySwiper", {
        loop: true,
        spaceBetween: 20,
        autoplay: {
            delay: 3000,
            disableOnInteraction: false,
        },
        pagination: {
            el: ".swiper-pagination",
            clickable: true,
            dynamicBullets: true,
        },
        navigation: {
            nextEl: ".swiper-button-next",
            prevEl: ".swiper-button-prev",
        },
        breakpoints: {
            0: { slidesPerView: 1 },
            768: { slidesPerView: 2 },
            1024: { slidesPerView: 3 },
        },
    });
}


document.getElementById("addRice").addEventListener("click", function (e) {
    e.preventDefault(); // stop page reload

    // Product details from your HTML
    let name = "Rice";
    let price = 60;
    let qty = "200kg";

    // Get cart from localStorage or create a new one
    let cart = JSON.parse(localStorage.getItem("cart-btn")) || [];

    // Check if item already exists in cart
    // Check if item already exists in cart
    let existingItem = cart.find(item => item.name === name);

    if (existingItem) {
        existingItem.count += 1; // Increase quantity
    } else {
        cart.push({ name, price, qty, count: 1 });
    }

    // Save back to localStorage
    localStorage.setItem("cart-btn", JSON.stringify(cart));
});


