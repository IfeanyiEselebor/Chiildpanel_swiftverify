document.addEventListener("DOMContentLoaded", function () {
    const resetForm = document.getElementById("reset_password");
    const notyf = setupNotifications(); // Initialize Notyf for notifications

    resetForm.addEventListener("submit", function (event) {
        event.preventDefault(); // Prevent page reload

        const emailInput = document.getElementById("email");
        const email = emailInput.value.trim();

        if (!email) {
            notyf.error("Please enter your email address.");
            return;
        }

        // Disable button to prevent multiple clicks
        const resetBtn = document.getElementById("forgot-btn");
        resetBtn.disabled = true;
        resetBtn.innerHTML = "Processing...";

        fetch("/reset-password", {
            method: "POST",
            headers: {
                "Content-Type": "application/x-www-form-urlencoded",
            },
            body: new URLSearchParams({ email: email }),
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    notyf.success({
                        message: data.message,
                        duration: 5000 // Delay in milliseconds (e.g., 5000ms = 5 seconds)
                    });
                    resetForm.reset();
                } else {
                    notyf.error(data.message);
                }
            })
            .catch(error => {
                console.error("Error:", error);
                notyf.error("An unexpected error occurred.");
            })
            .finally(() => {
                resetBtn.disabled = false;
                resetBtn.innerHTML = "Reset";
            });
    });
});

// Notyf notification setup function
function setupNotifications() {
    return new Notyf({
        duration: 3000,
        position: { x: "right", y: "top" },
        types: [
            {
                type: "warning",
                backgroundColor: "#ffc107",
                icon: {
                    className: "notyf__icon--error",
                    tagName: "i",
                },
            },
        ],
    });
}
