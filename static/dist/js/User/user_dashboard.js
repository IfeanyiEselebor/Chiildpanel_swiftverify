const statusText = document.getElementById("status-text");
const numberText = document.getElementById("number-text");
const service_information = document.getElementById("service_information");
$(document).ready(function () {
  /* Number Ordering Porcess*/
  $(document).on("click", "#order_number", function() {
    $('.order-number-btn').prop('disabled', true);
    $.ajax({
      type: "POST",
      url: "/order_number",
      contentType: "application/json",data: JSON.stringify({}),
      data: JSON.stringify({
              product_id : $(this).data('id')}
            ),
      encode: true,
    }).done(function(data) {
      /* Order Sequence */
      if (data['status'] == "Login Required") {
        /* Move to Login Page */
        const baseUrl = window.location.origin;
        window.location.replace(baseUrl +"/login");
      }
      if (data['status'] == "Insufficient Balance") {
            const Toast = Swal.mixin({
                toast: true,
                position: "top-end",
                showConfirmButton: false,
                timer: 3000,
                width: '12em',
                customClass: {
                    popup: 'bg-danger',
                    icon: 'no-border'
                },
                color: 'white',
                iconColor: 'white'
            });
            Toast.fire({
                iconHtml: '<i class="fa fa-times"></i>',
                title: 'Insufficient Balance'
            });
        }
      if (data['status'] == "Numbers Received") {
        const baseUrl = window.location.origin;
        window.location.replace(baseUrl +"/order/"+data['order_no']);
      } else {
        $('.order-number-btn').prop('disabled', false);
        numberText.classList.remove("d-none");
        statusText.classList.add("d-none");
        service_information.classList.add("d-none");
      }
    });
  });
  $("form").submit(function (event) {
    document.getElementById("check_av_button").disabled = true;
    var servicesl = $("#services").val();
    var countryl = $("#country").val();
    $.ajax({
      type: "POST",
      url: "/check-av",
      contentType: "application/json",
      data: JSON.stringify({
              country : $("#country").val(),
              services : $("#services").val() }
            ),
      encode: true,
    }).done(function (data) {
      if (data['status'] == "Login Required") {
        /* Move to Login Page */
        const baseUrl = window.location.origin;
        window.location.replace(baseUrl +"/login");
      }
      if (data == "Number Not available") {
        statusText.classList.remove("d-none");
        numberText.classList.add("d-none");
        service_information.classList.add("d-none");
        document.getElementById("check_av_button").disabled = false;
      } else {
        statusText.classList.add("d-none");
        numberText.classList.add("d-none");
        service_information.classList.remove("d-none");
        document.getElementById('Service_list').textContent = `${countryl} ${servicesl}`;
        document.getElementById("check_av_button").disabled = false;
        $('#Service_info').empty();
        const providersData = data['providers'] // assume this is the array of provider data objects

        providersData.forEach((provider) => {
          let success_rate_class;
          let fund_wallet_class;
          let order_number_class;

          if (provider.success_rate > 50) {
            success_rate_class = "text-success";
          } else {
            success_rate_class = "text-danger";
          }

          if (parseInt(document.getElementById("wallet_balance").innerText) < parseInt(provider.amount)) {
            fund_wallet_class = "";
            order_number_class = "d-none";
          } else {
            fund_wallet_class = "d-none";
            order_number_class = "";
          }

          const html = `
            <div class="row mt-2">
              <div class="col-4">
                <p> Price </p>
                <p>₦ <span id="price">${provider.amount}</span></p>
              </div>
              <div class="col-3">
                
              </div>
              <div class="col-5">
                <p> Success Rate </p>
                <p class="${success_rate_class}" id="success_rate">${provider.success_rate}%</p>
              </div>
              <button class="btn btn-primary w-100 ${order_number_class}" type="button" data-id="${provider.id}" id="order_number">
                Order Number <i class="bi bi-sim"></i>
              </button>
              <a href="/fund-wallet" id="fund_wallet" class="btn btn-primary text-white ${fund_wallet_class}">Fund Wallet</a>
            </div>
          `;

          const container = document.getElementById('Service_info');
          if (container.childNodes.length > 0) {
            container.innerHTML += '<br>';
          }
          // append the HTML to a container element
          container.innerHTML += html;
        });
      }
    });

    event.preventDefault();
  });

});
