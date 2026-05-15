const ForgotPassword = {
  init: () => {
    $(document).ready(() => {
      // Notification setup
      const notyfInstance = new Notyf({
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
      // Password Toggle functionality
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

      $("#forgot_password").submit((event) => {
        event.preventDefault();
        document.getElementById("forget_password_btn").disabled = true
        $.ajax({
          type: "POST",
          url: "/reset_password",
          contentType: "application/json",
          data: JSON.stringify({
            email: $("#youremail").val(),
            code: $("#otp-code").val(),
            password: $("#yourPassword").val()
          }),
          encode: true
        }).done((data) => {
          switch (data.status) {
            case "Email address isn't registered yet":
              notyfInstance.error("Email address isn't registered yet!");
              $("#youremail").addClass("is-invalid");
              break;
            case "Invalid Otp":
              notyfInstance.error("Please enter a valid otp code !");
              $("#otp-code").addClass("is-invalid");
              break;
            case "OTP Expired":
              notyfInstance.error("Otp code has expired!");
              $("#otp-code").addClass("is-invalid");
              break;
            case "Password Change Successfully":
              $("form")[0].reset();
              notyfInstance.success("Login Successfully");
              setTimeout(() => {
                window.location.href = window.location.origin + data.url;
              }, 2000); // adjust the delay time in milliseconds (2000 = 2 seconds)
              break;
            default:
              console.error("Unknown response status:", data.status);
          }
          document.getElementById("forget_password_btn").disabled = false;
        });
      });

      // Send OTP functionality
      $(document).on("click", "#send_otp_btn", () => {
        document.getElementById("send_otp_btn").disabled = true;
        $.ajax({
          type: "POST",
          url: "/password-code",
          contentType: "application/json",
          data: JSON.stringify({ email: $("input[name='email']").val() }),
          encode: true
        }).done((data) => {
          switch (data.status) {
            case "Login Required":
              window.location.replace(window.location.origin + "/login");
              break;
            case "Email address isn't registered yet":
              document.getElementById("send_otp_btn").disabled = false;
              notyfInstance.error("Email address isn't registered yet");
              $("#youremail").addClass("is-invalid");
              break;
            case "Otp Sent Successfully":
              const button = document.getElementById("send_otp_btn");
              button.disabled = true;
              let timeLeft = 60;
              const timer = setInterval(() => {
                timeLeft--;
                button.textContent = `Resend code: ${timeLeft}s`;
                if (timeLeft === 0) {
                  clearInterval(timer);
                  button.disabled = false;
                  button.textContent = "Send Code";
                }
              }, 1000);
              break;
            default:
              console.error("Unknown response status:", data.status);
          }
        });
      });

      // Remove error class on input focus
      $("#youremail").on("click", () => {
        $("#youremail").removeClass("is-invalid");
      });

      // Enable/Disable forgot password button
      document.getElementById("yourPassword").addEventListener("keyup", () => {
        if ($("#yourPassword").val() === "") {
          document.getElementById("forget_password_btn").disabled = true;
        } else {
          document.getElementById("forget_password_btn").disabled = $("#youremail").hasClass("is-invalid") || $("#yourPassword").val() === "";
        }
      });
    });
  }
};

ForgotPassword.init();