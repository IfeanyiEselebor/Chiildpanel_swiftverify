const sound = new Audio(`${window.location.origin}/static/dist/user/notification/sound_2.mp3`);
let toastDisplayed = false;
let progressBar;
const API_BASE_URL = `${window.location.origin}/api`;
const api_key = localStorage.getItem("apiKey") || "";

// Notification setup
const notyf = new Notyf({
  duration: 1000,
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

// OTP Copy Event Listener
$(document).on("click", ".copy-otp-btn", handleOtpCopy);

function handleOtpCopy(event) {
  if (!toastDisplayed) {
    const otpCode = $(event.currentTarget).closest(".sms-div").find("#otp-code").text();
    navigator.clipboard.writeText(otpCode);
    notyf.success("Copied!");
    toastDisplayed = true;
    setTimeout(() => { toastDisplayed = false; }, 5000);
  }
}

function handleNumberCopy(elementId) {
  if (!toastDisplayed) {
    navigator.clipboard.writeText(document.getElementById(elementId).innerText);
    notyf.success("Copied!");
    toastDisplayed = true;
    setTimeout(() => { toastDisplayed = false; }, 1000);
  }
}

function updateOrderStatus(status, iconClass) {
  $("#span-status").text(status);
  $("#status-icon").attr("class", `fa-regular ${iconClass}`);
  $("#buy-next-number-div").removeClass("d-none");
  $("#cancel-number-div").addClass("d-none");
}

$(document).ready(function () {
  $("#cancel-number").click(cancelOrder);
  $("#finish-number").click(finishOrder);
  $("#buy-next-number-btn").click(nextOrder);
  $("#get-more-btn").click(getMoreCode);

  if ($("#span-status").text() === "Received" &&
      (document.querySelectorAll("#code_div .enabled-otp").length === 0 ||
          document.getElementById("get-more-btn").getAttribute("data-check_status") === "1" )) {
    const expirationTime = $("#time").text();
    const duration = parseInt($("#duration").text(), 10);
    const result = calculateTime(expirationTime);
    handleInitialTimeoutCheck(result, duration);
  }
});

function cancelOrder() {
  const orderNumber = $("#cancel-number").data("order_no");
  $.get(`${API_BASE_URL}/setStatus?api_key=${api_key}&id=${orderNumber}&status=8`, function(response) {
    if (response === "ACCESS_CANCEL") {
      updateOrderStatus("Canceled", "fa-circle-xmark text-danger");
      clearInterval(progressBar);
    } else if (response === "EARLY_CANCEL_DENIED") {
      notyf.error("It is possible to cancel the number after two minutes of purchase");
    } else {
      processOrderResponse(response);
    }
  });
}

function processOrderResponse(response) {
  if (response.status === "Received" && response.sms) {
    const count = document.querySelectorAll("#code_div .enabled-otp").length;
    if(response.sms.length > count){
      renderOtpCodes(response.sms);
      updateOrderStatus("Received", "fa-circle-check text-success");
      sound.play();
      let getMoreBtn = document.getElementById("get-more-btn");
      if (getMoreBtn.classList.contains("disabled")) {
          getMoreBtn.classList.remove("disabled"); // Remove Bootstrap disabled class
          getMoreBtn.removeAttribute("disabled");  // Remove actual disabled attribute
      }
    }
  } else if (response.status === "Finished") {
    if (response.sms.length > 0){
      renderOtpCodes(response.sms);
    }
    updateOrderStatus("Finished", "fa-circle-check text-success");
    sound.play();
  } else if (response.status === "Timeout") {
    $("#wallet_balance").text(response.balance)
    updateOrderStatus("Timeout", "fa-clock text-warning");
    document.getElementById("timeout_alert").classList.remove("d-none");
    clearInterval(progressBar);
  }
}

function handleInitialTimeoutCheck(result, duration) {
  const orderNumber = $("#cancel-number").data("order_no");
  if (result === "Time has passed") {
    checkOrderStatus(orderNumber);
  } else {
    updateTimerDisplay(result);
    updateTimerWidth(result, duration);
    progressBar = setInterval(updateProgress, 1000);
    checkOrderStatus(orderNumber);
  }
}

function updateTimerDisplay(result) {
  $("#minutes-left").text(result.minutes === 0 ? `${result.seconds} seconds left` : `${result.minutes} minutes left`);
}

function updateTimerWidth(result, duration) {
  $("#timer").css("width", `${calculateWidthPercentage(result.minutes, result.seconds, duration)}%`);
}

function calculateTime(endTime) {
  const currentTime = new Date().toLocaleString("en-US", { timeZone: "Africa/Lagos" });
  const timeDiffInMs = new Date(endTime) - new Date(currentTime);
  return timeDiffInMs <= 0 ? "Time has passed" : { minutes: Math.floor(timeDiffInMs / 60000), seconds: Math.floor((timeDiffInMs % 60000) / 1000) };
}

function calculateWidthPercentage(remainingMinutes, remainingSeconds, totalDurationInMinutes) {
  return ((remainingMinutes + remainingSeconds / 60) / totalDurationInMinutes * 100).toFixed(2);
}

function checkOrderStatus(orderId) {
  $.get(`${API_BASE_URL}/getStatus?api_key=${api_key}&id=${orderId}`).done(processOrderResponse);
}

function renderOtpCodes(smsArray) {
  const codeDiv = $("#code_div").empty();
  smsArray.forEach(code => {
    codeDiv.append(
      `<div class="sms-div mb-2">
        <p class="code-p"><span class="span-code" id="otp-code">${code}</span></p>
        <button class="enabled-otp copy-otp-btn" tabindex="0" type="button">
          <img alt="Copy" src="/static/dist/img/copy.8ca81180.svg" width="24" height="24">
        </button>
      </div>`
    );
  });
  $(".copy-otp-btn").off("click").on("click", handleOtpCopy);
  $("#cancel-number").addClass("d-none");
  $("#finish-number").removeClass("d-none");
}

function finishOrder() {
  const orderNumber = $("#cancel-number").data("order_no");
  $.get(`${API_BASE_URL}/setStatus?id=${orderNumber}&status=6`).done(response => {
    if (response === "Number Activation Finished") {
      renderOtpCodes(response.sms);
      updateOrderStatus("Finished", "fa-circle-check text-success");
      sound.play();
    }
  });
}

function nextOrder() {
  const poolValue = $("input[name='pool']").val();
  const orderValues = $(".order-line .order-end").map((_, el) => $(el).text().trim()).get();
  $.get(`${API_BASE_URL}/getNumber?api_key=${api_key}&service=${orderValues[1]}&country=${orderValues[2]}&pool=${poolValue}`).done(data => {
    if (data.id) {
      notyf.success("Numbers Ordered Successfully");
      setTimeout(() => window.location.replace(`${window.location.origin}/order/${data.id}`), 1500);
    }
  });
}

function getMoreCode() {
  const orderNumber = $("#cancel-number").data("order_no");
  $.get(`${API_BASE_URL}/setStatus?id=${orderNumber}&status=3`).done(response => {
    if (response === "ACCESS_RETRY_GET") {
      let getMoreBtn = document.getElementById("get-more-btn");
      getMoreBtn.classList.add("disabled");  // Adds Bootstrap's disabled class
      getMoreBtn.setAttribute("disabled", "disabled");  // Adds the disabled attribute
      let checkStatus = getMoreBtn.getAttribute("data-check_status");
      getMoreBtn.setAttribute("data-check_status", "1");
      checkOrderStatus(orderNumber);
    }
  });
}

// Update progress bar and remaining time
function updateProgress() {
  const expirationTime = document.getElementById("time").innerText;
  const duration = parseInt(document.getElementById("duration").innerText, 10);
  const result = calculateTime(expirationTime);
  const orderNumber = $("#cancel-number").data("order_no");
  checkOrderStatus(orderNumber);
  if (result === "Time has passed"){
    $("#minutes-left").text('0 seconds left');
  } else {
    updateTimerDisplay(result);
    updateTimerWidth(result, duration);
  }
}