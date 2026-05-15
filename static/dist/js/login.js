document.addEventListener('DOMContentLoaded', function() {
    const notyf = setupNotifications();
    setupPasswordToggle();
    setupLoginForm(notyf);
    checkRegistrationCookie(notyf);
    clearLocalStorage();
});

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

function setupPasswordToggle() {
    document.querySelectorAll('.password-toggle').forEach(toggle => {
        toggle.addEventListener('click', function() {
            const input = this.closest('.input-group').querySelector('input');
            const icon = this.querySelector('i');

            this.classList.toggle('active');
            input.type = this.classList.contains('active') ? 'text' : 'password';
            icon.classList.toggle('fa-eye-slash', input.type === 'password');
            icon.classList.toggle('fa-eye', input.type === 'text');
        });
    });
}

function setupLoginForm(notyf) {
    const form = document.getElementById('login_user');
    if (!form) return;

    form.addEventListener('submit', function(event) {
        event.preventDefault();
        const loginBtn = document.getElementById('login-btn');
        loginBtn.disabled = true;

        const formData = {
            username: form.querySelector('input[name="username"]').value,
            password: form.querySelector('input[name="password"]').value,
            // turnstile_response: form.querySelector('input[name="cf-turnstile-response"]').value,
            remember_me: form.querySelector('#rememberMe').checked
        };

        fetch('/login-user', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(formData),
        })
        .then(response => response.json())
        .then(data => handleLoginResponse(data, notyf, form))
        .catch(error => {
            console.error('Error:', error);
            notyf.error('An error occurred during login');
        })
        .finally(() => {
            loginBtn.disabled = false;
        });
    });
}

function handleLoginResponse(data, notyf, form) {
    switch (data.status) {
        case 'Login Successful':
            handleSuccessfulLogin(data);
            break;
        case 'User has been ban':
            notyf.error(`User has been banned due to ${data.data}`);
            resetForm(form);
            reloadTurnstile();  // Reload the Turnstile
            break;
        case 'Username or password not correct':
            notyf.error('Username or password not correct');
            reloadTurnstile();  // Reload the Turnstile
            break;
        case 'Captcha not Solved':
            notyf.error('Captcha not Solved');
            reloadTurnstile();  // Reload the Turnstile
            break;
        default:
            notyf.error('An unexpected error occurred');
            reloadTurnstile();  // Reload the Turnstile
    }
}

function handleSuccessfulLogin(data) {
    if (data.rememberme) {
        setCookie('rememberme', data.rememberme, 30);
    } else {
        deleteCookie('rememberme', '/');
    }
    localStorage.setItem("apiKey", data.apiKey);
    window.location.href = `${window.location.origin}${data.url}`;
}

function resetForm(form) {
    form.reset();
    const rememberMeCheckbox = form.querySelector('#rememberMe');
    if (rememberMeCheckbox) {
        rememberMeCheckbox.checked = false;
    }
}

function checkRegistrationCookie(notyf) {
    if (getCookie('userReg')) {
        notyf.success('User Registration Successfully');
        deleteCookie('userReg', '/');
    }
}

function clearLocalStorage() {
    localStorage.removeItem('cart');
    localStorage.removeItem('apiKey');
}

function setCookie(name, value, days) {
    const date = new Date();
    date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
    const expires = `; expires=${date.toUTCString()}`;
    document.cookie = `${name}=${value || ''}${expires}; path=/`;
}

function deleteCookie(name, path) {
    document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=${path};`;
}

function getCookie(name) {
    const nameEQ = name + '=';
    const ca = document.cookie.split(';');
    for (let i = 0; i < ca.length; i++) {
        let c = ca[i];
        while (c.charAt(0) === ' ') c = c.substring(1, c.length);
        if (c.indexOf(nameEQ) === 0) return c.substring(nameEQ.length, c.length);
    }
    return null;
}

function reloadTurnstile() {
    if (typeof turnstile !== 'undefined') {
        turnstile.reset(); // Reset the Turnstile widget
    }
}
