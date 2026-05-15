const API_BASE_URL = 'http://127.0.0.1:5000//api';
const api_key = localStorage.getItem("apiKey") || "";

// Utility function to calculate time difference
const calculateTime = (endTime) => {
  const currentTime = new Date().toLocaleString("en-US", { timeZone: "Africa/Lagos" });
  const currentTimeObj = new Date(currentTime);
  const endTimeObj = new Date(endTime);

  const timeDiffInMs = endTimeObj.getTime() - currentTimeObj.getTime();
  const minutes = Math.floor(timeDiffInMs / 60000);
  const seconds = Math.floor((timeDiffInMs % 60000) / 1000);

  return timeDiffInMs <= 0 ? "Time has passed" : { minutes, seconds };
};

// Polling function to check order updates
const checkOrderUpdates = (table, sound, orderId) => {
  $.get(`${API_BASE_URL}/getStatus?api_key=${api_key}&id=${orderId}`, function(data) {
    if (data.status === "Received" && !data.sms) {
      setTimeout(() => checkOrderUpdates(table, sound, orderId), 5000);
    } else if (data.status === "Received" && data.sms) {
      table.ajax.reload();
      sound.play();
    }
  }).fail(function() {
    console.error("Error fetching order status");
  });
};

// Function to poll orders for updates
const pollOrders = (table, sound, jsonData) => {
  jsonData.forEach(order => {
    const orderStatus = $(order.status).attr("title"); // Extract "title" attribute from status HTML
    const orderId = order.id; // Directly get order ID from JSON

    if (orderStatus === "Received" && orderId) {

      // Extract expiration time from the status HTML
      const dataExpiration = $(order.status).attr("data-expiration");

      // Check if the order is still waiting for an SMS code
      $.get(`${API_BASE_URL}/getStatus?api_key=${api_key}&id=${orderId}`, function(data) {
        if (dataExpiration) {
          const result = calculateTime(dataExpiration);
           if (result === "Time has passed") {
            $("#wallet_balance").text(data.balance);
            table.ajax.reload();
            return;
          }
        }
        if (data.status === "Received" && (!data.sms || data.check_status === true)) {
          checkOrderUpdates(table, sound, orderId);
        }
      }).fail(function() {
        console.error(`❌ Error fetching status for order ${orderId}`);
      });
    }
  });

  // // Run this function again after 5 seconds
  // setTimeout(() => pollOrders(table, sound, jsonData), 5000);
};

// DataTable initialization
const initializeDataTable = (sound) => {
  return $('#orders').DataTable({
    responsive: true,
    ajax: {
      type: "GET",
      url: '/load-history',
      dataSrc: function (json) {
        if (json.data.status === "Login Required") {
          location.reload();
        } else {
          return json.data;
        }
      }
    },
    columns: [
      { data: 'id' },
      { data: 'date' },
      { data: 'service' },
      { data: 'country' },
      { data: 'Number' },
      { data: 'Code' },
      { data: 'amount' },
      { data: 'status' }
    ],
    order: [[1, "desc"]],
    columnDefs: [
      { targets: [7], className: "dt-center" }
    ],
    initComplete: function() {
      const table = this.api(); // Get DataTable instance
      const data = this.api().data().toArray();
      pollOrders(table, sound, data); // Start polling after DataTable is ready
    }
  });
};

// Main Execution
document.addEventListener("DOMContentLoaded", function() {
  const sound = new Audio(window.location.origin + '/static/dist/user/notification/sound_2.mp3');
  const table = initializeDataTable(sound);
});
