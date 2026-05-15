

document.addEventListener("DOMContentLoaded", function() {
    // Password Toggle Functionality
    setupPasswordToggle();

    // Notification setup
    const notyf = setupNotifications();

    // Password validation
    setupPasswordValidation(notyf);

    // Form submission
    setupFormSubmission(notyf);
});

function setupPasswordToggle() {
    const passwordToggles = document.querySelectorAll('.password-toggle');
    passwordToggles.forEach(toggle => {
        toggle.addEventListener('click', function() {
            const input = this.closest('.input-group').querySelector('input');
            const icon = this.querySelector('i');

            this.classList.toggle('active');
            if (this.classList.contains('active')) {
                input.type = 'text';
                icon.classList.replace('fa-eye-slash', 'fa-eye');
            } else {
                input.type = 'password';
                icon.classList.replace('fa-eye', 'fa-eye-slash');
            }
        });
    });
}

function setupNotifications() {
    return new Notyf({
        duration: 3000,
        position: { x: 'right', y: 'top' },
        types: [
            {
                type: "warning",
                backgroundColor: "#ffc107",
                icon: {
                    className: "notyf__icon--error",
                    tagName: "i"
                }
            }
        ]
    });
}

function setupPasswordValidation(notyf) {
    const passwordInput = document.getElementById("yourPassword");
    const confirmPasswordInput = document.getElementById("yourConfirmPassword");
    const registerBtn = document.getElementById("register-btn");

    function validatePasswords() {
        const isMatch = passwordInput.value === confirmPasswordInput.value;
        const isEitherFilled = passwordInput.value !== "" || confirmPasswordInput.value !== "";

        if (isEitherFilled) {
            const isValid = isMatch && passwordInput.value !== "" && confirmPasswordInput.value !== "";

            passwordInput.classList.toggle("is-invalid", !isValid);
            confirmPasswordInput.classList.toggle("is-invalid", !isValid);
            registerBtn.disabled = !isValid;

            if (!isMatch) {
                notyf.error("Passwords don't match");
            }
        } else {
            // If both fields are empty, remove any validation styling
            passwordInput.classList.remove("is-invalid");
            confirmPasswordInput.classList.remove("is-invalid");
            registerBtn.disabled = false;
        }
    }

    passwordInput.addEventListener("blur", validatePasswords);
    confirmPasswordInput.addEventListener("blur", validatePasswords);
}

function setupFormSubmission(notyf) {
    const form = document.forms["register_user"];

    form.addEventListener("submit", function(event) {
        event.preventDefault();
        document.getElementById("register-btn").disabled = true;

        const formData = {
            username: form.username.value,
            email: form.email.value,
            turnstile_response: form.querySelector('input[name="cf-turnstile-response"]').value,
            password: form.password.value
        };

        fetch("/register-user", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(formData),
        })
        .then(response => response.json())
        .then(data => handleRegistrationResponse(data, form, notyf))
        .catch(error => {
            console.error("Error:", error);
            notyf.error("An error occurred during registration");
        })
        .finally(() => {
            document.getElementById("register-btn").disabled = false;
        });
    });
}

function handleRegistrationResponse(data, form, notyf) {
    switch (data.message) {
        case "Username already exists":
            form.username.value = "";
            notyf.error("Username Already Exists");
            reloadTurnstile();  // Reload the Turnstile
            break;
        case "Email already exists":
            form.email.value = "";
            notyf.error("Email Address Already Registered");
            reloadTurnstile();  // Reload the Turnstile
            break;
        case "User Registration Successfully":
            resetForm(form);
            document.cookie = "userReg=1";
            window.location.href = `${window.location.origin}/login`;
            break;
        case 'Captcha not Solved':
            notyf.error('Captcha not Solved');
            reloadTurnstile();  // Reload the Turnstile
            break;
        default:
            notyf.error("An unexpected error occurred");
    }
}

function resetForm(form) {
    form.reset();
    document.getElementById("acceptTerms").checked = false;
}

function reloadTurnstile() {
    if (typeof turnstile !== 'undefined') {
        turnstile.reset(); // Reset the Turnstile widget
    }
}
