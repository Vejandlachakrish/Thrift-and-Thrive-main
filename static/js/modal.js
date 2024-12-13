// Open modal
function openModal() {
    document.getElementById("loginModal").style.display = "block";
}

// Close modal
function closeModal() {
    document.getElementById("loginModal").style.display = "none";
}

// Switch to Register Form
function switchToRegister() {
    document.getElementById("loginForm").style.display = "none";
    document.getElementById("registerForm").style.display = "block";
}

// Switch to Login Form
function switchToLogin() {
    document.getElementById("registerForm").style.display = "none";
    document.getElementById("loginForm").style.display = "block";
}

// Close modal if clicking outside
window.onclick = function(event) {
    if (event.target == document.getElementById("loginModal")) {
        closeModal();
    }
}
