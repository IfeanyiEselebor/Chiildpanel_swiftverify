$(document).ready(function() {
  /* Query Transaction Status*/
  $(document).on("click", "#query-btn", function() {
    var transactionId = $(this).data("transaction_id");
    $.ajax({
      type: "POST",
      url: "/query-transaction",
      contentType: "application/json",
      data: JSON.stringify({ transaction_id: transactionId }),
      encode: true,
    }).done(function(data) {
      /* Reload Page */
      window.location.reload();
    });
  });

  /* Initiate Datatables */
  var table = $('#orders').DataTable({
    responsive: true,
    ajax: {
      type: "GET",
      url: '/load-history',
      dataSrc: function(json) {
        // Check if the response was successful
        if (json.data['status'] === "Login Required") {
          /* Reload Page */
          location.reload();
        } else {
          json.data.filter(item => {
            const statusElement = $(item.status);
            return statusElement.attr('aria-label') === 'Received';
          }).forEach(item => {
            checkCode(item);
          });
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
    ]
  });


  function checkCode(item) {
    const dataExpiration = $(item.status).attr('data-expiration');
    const dataAmount = $(item.status).attr('data-amount');
    result = calculateTime(dataExpiration)
    if (result === "Time has passed") {
      $.ajax({
        type: "POST",
        url: "/timeout-order",
        contentType: "application/json",
        data: JSON.stringify({
            order_no: item.id,
            amount: dataAmount
        }),
        encode: true
      }).done(function (data) {
          if (data['status'] === "Login Required") {
            window.location.replace(window.location.origin + "/login");
          } else if (data['status'] === "Timeout Successfully"){
            $("#wallet_balance").text(data['amount'])
            table.ajax.reload();
          }
      });
    }else{
      $.ajax({
        type: 'POST',
        url: '/get_code',
        contentType: "application/json",
        data: JSON.stringify({
            order_no: item.id
        }),
        success: function(response) {
            if (response === "{}") {
                window.location.replace(window.location.origin + "/login");
            } else if (response['status'] === "Code Successfully") {
              table.ajax.reload();
            } else {
              // Code not received, try again after a short delay
              setTimeout(function() {
                checkCode(item);
              }, 10000); // adjust the delay as needed
            }
        }
      });
    }
  }
});

function calculateTime(endTime) {
  const currentTime = new Date();
  const endTimeObj = new Date(endTime);

  const timeDiffInMs = endTimeObj.getTime() - currentTime.getTime();
  const minutes = Math.floor(timeDiffInMs / 60000);
  const seconds = Math.floor((timeDiffInMs % 60000) / 1000);

  return timeDiffInMs <= 0 ? "Time has passed" : { minutes: minutes, seconds: seconds };
}