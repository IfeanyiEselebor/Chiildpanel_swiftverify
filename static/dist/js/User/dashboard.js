const statusText = document.getElementById("status-text");
const numberText = document.getElementById("number-text");
const service_information = document.getElementById("service_information");
let services_val;
let country_val;
const api_key = localStorage.getItem("apiKey") || "";
const baseUrl = window.location.origin;

const notyf = new Notyf({
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

const check_av = (event) => {
    event.preventDefault();
    document.getElementById("check_av_button").disabled = true;

    services_val = $("#services").val();
    country_val = $("#country").val();

    $.ajax({
        url: `${baseUrl}/api/getPrices?api_key=${api_key}&service=${services_val}&country=${country_val}`,
        type: "GET",
        dataType: "json",
        success: (data) => {
            displayProviders(data);
            document.getElementById("check_av_button").disabled = false;
        },
        error: (xhr) => {
            console.error("Error fetching provider data:", xhr);
            notyf.open({ type: "warning", message: "Error fetching provider data." });
            document.getElementById("check_av_button").disabled = false;
        }
    });
};

const displayProviders = (data) => {
    $("#Service_info").empty();
    numberText.classList.add("d-none");
    statusText.classList.add("d-none");
    service_information.classList.remove("d-none");

    let providerData = data[country_val]?.[services_val];
    if (!providerData) {
        statusText.classList.remove("d-none");
        return;
    }

    let success_rate_class = "text-danger";
    Object.entries(providerData).forEach(([id, details]) => {
        let { order_amount, pool,  success_rate } = details;
        let max_price = order_amount;

        if (success_rate > 50) {
            success_rate_class = "text-success";
        }

        let fund_wallet_class;
        let order_number_class;

        if (parseInt(document.getElementById("wallet_balance").innerText) < parseInt(order_amount)) {
            fund_wallet_class = "";
            order_number_class = "d-none";
        } else {
            fund_wallet_class = "d-none";
            order_number_class = "";
        }

        let html = `
          <div class="row mt-2">
             <div class="col-4">
                <p> Price </p>
                <p>₦ <span id="price">${order_amount}</span></p>
                </div>
                <div class="col-3">
                
                </div>
                <div class="col-5">
                <p> Success Rate </p>
                <p class="${success_rate_class}" id="success_rate">${success_rate}%</p>
                </div>
            ${pool === "Alpha"? `
                <div class="input-group mb-0 flex-column flex-md-row">
                <div class="d-flex w-100">
                    <div class="input-group-prepend">
                    <label class="input-group-text" for="area_code">Area codes</label>
                    </div>
                    <input type="text" class="form-control" name="area_code" placeholder="503, 202, 404">
                </div>
                <p class="text-xs opacity-60 py-1 px-2 w-100 mt-2 mt-md-0">Preferred area codes. Increases price by 20%.</p>
                </div>
                <div class="input-group mb-0 flex-column flex-md-row">
                <div class="d-flex w-100">
                    <div class="input-group-prepend">
                    <label class="input-group-text" for="carriers">Carriers</label>
                    </div>
                    <input type="text" class="form-control" name="carriers" placeholder="tmo, vz, att">
                </div>
                <p class="text-xs opacity-60 py-1 px-2 w-100 mt-2 mt-md-0">Preferred carrier. Increases price by 20%.</p>
                </div>
                <div class="input-group mb-0 flex-column flex-md-row">
                <div class="d-flex w-100">
                    <div class="input-group-prepend">
                    <label class="input-group-text" for="phone">Phone</label>
                    </div>
                    <input type="text" class="form-control" name="phone" placeholder="1112223333">
                </div>
                <p class="text-xs opacity-60 py-1 px-2 w-100 mt-2 mt-md-0">Preferred phone. Increases price by 20%.</p>
                </div>
            ` : ''}
          <button class="btn btn-primary w-100 order-number-btn ${order_number_class}" type="button" data-id="${pool}" id="order_number" onclick="order_number(event, '${pool}', ${max_price})">
            Order Number <i class="bi bi-sim"></i>
          </button>
          <a href="/fund-wallet" id="fund_wallet" class="btn btn-primary text-white ${fund_wallet_class}">Fund Wallet</a>
        `;

        $("#Service_info").append(html);
    });
};

const order_number = (event, pool, max_price) => {
    $('.order-number-btn').prop('disabled', true);

    let area_code = $('input[name="area_code"]').val() || "";
    let carriers = $('input[name="carriers"]').val() || "";
    let phone = $('input[name="phone"]').val() || "";

    $.ajax({
        url: `${baseUrl}/api/getNumber?api_key=${api_key}&service=${services_val}&country=${country_val}&pool=${pool}&max_price=${max_price}&areas=${area_code}&carriers=${carriers}&number=${phone}`,
        type: "GET",
        dataType: "json",
        success: (data) => {
            if (data === "NO_MONEY"){
                notyf.open({ type: "danger", message: "Insufficient Balance." });
            }
            if (data === "NO_NUMBERS"){
                notyf.open({ type: "warning", message: "No numbers available. Try again later." });
                $('.order-number-btn').prop('disabled', false);
            }
            if (data.id) {
                window.location.replace(`order/${data.id}`);
            }
        },
        error: (xhr) => {
            console.error("Error ordering number:", xhr);
            notyf.open({ type: "warning", message: "Error ordering number." });
            $('.order-number-btn').prop('disabled', false);
        }
    });
};
