// Constants
const POLLING_INTERVAL = 5000;
const NOTIFICATION_DURATION = 3000;
const PRICE_INCREASE_PERCENTAGE = 20;
const API_BASE_URL = window.location.origin;

// DOM Elements with Null Checks
const statusText = document.getElementById("status-text") || { classList: { add: () => {}, remove: () => {} } };
const numberText = document.getElementById("number-text") || { classList: { add: () => {}, remove: () => {} } };
const service_information = document.getElementById("service_information") || { classList: { add: () => {}, remove: () => {} } };
let services_val;
let country_val;
const api_key = localStorage.getItem("apiKey") || "";
const baseUrl = window.location.origin;
const sound = new Audio(`${baseUrl}/static/dist/user/notification/sound_2.mp3`);

// Notification Setup
const notyf = new Notyf({
    duration: NOTIFICATION_DURATION,
    position: { x: 'right', y: 'top' },
    types: [
        { type: "warning", backgroundColor: "#ffc107", icon: { className: "notyf__icon--error", tagName: "i" } },
        { type: "error", backgroundColor: "#dc3545", icon: { className: "notyf__icon--error", tagName: "i" } },
        { type: "success", backgroundColor: "#28a745", icon: { className: "notyf__icon--success", tagName: "i" } }
    ]
});

// Utility Functions
const setLoading = (elementId, isLoading, text = 'Check Availability') => {
    const element = document.getElementById(elementId);
    if (element) {
        element.disabled = isLoading;
        element.textContent = isLoading ? 'Loading...' : text;
    }
};

function calculateTime(endTime) {
  // Convert `endTime` to ISO format and create a Date object
  const formattedEndTime = new Date(endTime.replace(" ", "T") + "Z");

  // Get current time in Africa/Lagos timezone in 24-hour format
  const options = {
    timeZone: "Africa/Lagos",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false // Ensures 24-hour format
  };

  // Format current time properly
  const currentTimeString = new Intl.DateTimeFormat("en-GB", options).format(new Date());
  const formattedCurrentTime = new Date(new Date().toLocaleString("en-US", { timeZone: "Africa/Lagos" }));

  // Calculate time difference in milliseconds
  const timeDiffInMs = formattedEndTime - formattedCurrentTime;

  // Return time difference
  return timeDiffInMs <= 0
    ? "Time has passed"
    : {
        minutes: Math.floor(timeDiffInMs / 60000),
        seconds: Math.floor((timeDiffInMs % 60000) / 1000)
      };
}

// Cancel Order Function
function cancelOrder(orderNumber, row, button) {
    // Disable the button before the request
    button.classList.add("disabled");
    button.setAttribute("disabled", "disabled");

    $.get(`${API_BASE_URL}/api/setStatus?api_key=${api_key}&id=${orderNumber}&status=8`, function(response) {
        console.log(`Cancel order response for ${orderNumber}:`, response);
        if (response === "ACCESS_CANCEL") {
            // Update row status to "Canceled"
            const rowData = row.data();
            rowData.status = '<span title="Canceled" data-expiration="">Canceled</span>';
            rowData.actions = ''; // Remove action buttons
            row.data(rowData).draw(false);
            notyf.open({ type: "success", message: "Order canceled successfully" });
        } else if (response === "EARLY_CANCEL_DENIED") {
            notyf.error("It is possible to cancel the number after two minutes of purchase");
            // Re-enable button on expected failure response
            button.classList.remove("disabled");
            button.removeAttribute("disabled");
        } else {
            notyf.error("Failed to cancel order: " + response);
            // Re-enable button on unexpected response
            button.classList.remove("disabled");
            button.removeAttribute("disabled");
        }
    }).fail(function(xhr, status, error) {
        console.error('Cancel order error:', error);
        notyf.error("Failed to cancel order: " + error);
        // Re-enable button on network failure
        button.classList.remove("disabled");
        button.removeAttribute("disabled");
    });
}
// Finish Order Function
function finishOrder(orderNumber, row) {
    $.get(`${API_BASE_URL}/api/setStatus?api_key=${api_key}&id=${orderNumber}&status=6`).done(response => {
        console.log(`Finish order response for ${orderNumber}:`, response);
        if (response === "Number Activation Finished") {
            const rowData = row.data();
            rowData.status = '<span title="Finished" data-expiration="">Finished</span>';
            rowData.actions = ''; // Remove action buttons
            row.data(rowData).draw(false);
            sound.play().catch(err => console.error('Audio play error:', err));
            notyf.open({ type: "success", message: "Order finished successfully" });
        } else {
            notyf.error("Failed to finish order: " + (typeof response === 'string' ? response : "Unknown error"));
        }
    }).fail(function(xhr, status, error) {
        console.error('Finish order error:', error);
        notyf.error("Failed to finish order: " + error);
    });
}

// Get More Code Function
function getMoreCode(orderNumber, button, table) {
    $.get(`${API_BASE_URL}/api/setStatus?api_key=${api_key}&id=${orderNumber}&status=3`).done(response => {
        console.log(`Get more code response for ${orderNumber}:`, response);
        if (response === "ACCESS_RETRY_GET") {
            // Disable the "Get More Code" button
            button.classList.add("disabled");
            button.setAttribute("disabled", "disabled");
            button.setAttribute("data-check_status", "1");
            notyf.open({ type: "success", message: "Requesting more codes..." });
            // Trigger status check (using existing checkOrderUpdates)
            checkOrderUpdates(table, sound, orderNumber);
        } else {
            notyf.error("Failed to get more codes: " + (typeof response === 'string' ? response : "Unknown error"));
        }
    }).fail(function(xhr, status, error) {
        console.error('Get more code error:', error);
        notyf.error("Failed to get more codes: " + error);
    });
}

// API Functions
const check_av = async (event) => {
    event.preventDefault();
    setLoading("check_av_button", true);

    try {
        services_val = $("#services").val();
        country_val = $("#country").val();
        if (!services_val || !country_val) throw new Error("Service or country not selected");

        const response = await $.ajax({
            url: `${baseUrl}/api/getPrices?api_key=${api_key}&service=${services_val}&country=${country_val}`,
            type: "GET",
            dataType: "json"
        });
        console.log('check_av response:', response);
        displayProviders(response);
    } catch (error) {
        console.error('check_av error:', error);
        if (error.responseText === 'NO_NUMBERS') {
            numberText.classList.remove("d-none");
        } else if (error.responseText === 'BAD_SERVICE') {
            statusText.classList.remove("d-none");
        }
        service_information.classList.add("d-none");
    } finally {
        setLoading("check_av_button", false);
    }
};

const displayProviders = (data) => {
    $("#Service_info").empty();
    numberText.classList.add("d-none");
    statusText.classList.add("d-none");
    service_information.classList.remove("d-none");

    const providerData = data[country_val]?.[services_val];
    if (!providerData) {
        console.warn('No provider data for:', country_val, services_val);
        statusText.classList.remove("d-none");
        return;
    }

    Object.entries(providerData).forEach(([id, details]) => {
        const { order_amount, pool, success_rate } = details;
        // pool_codename is the canonical Alpha/Bravo/… string from the parent.
        // `pool` may be the operator's renamed display label; we never key UI
        // logic off it. Fall back to `pool` so cards still render for any
        // pool the parent adds before pool_labels is seeded.
        const pool_codename = details.pool_codename || pool;
        // carrier is the SMSPool sub-pool id (Echo) or 5sim provider name
        // (Charlie). Empty for everything else. We pass it straight through
        // to the order endpoint without surfacing it in the UI.
        const carrier = details.carrier || "";
        const success_rate_class = success_rate > 50 ? "text-success" : "text-danger";
        const walletBalance = parseInt(document.getElementById("wallet_balance")?.innerText || 0);
        const fund_wallet_class = walletBalance < order_amount ? "" : "d-none";
        const order_number_class = walletBalance >= order_amount ? "" : "d-none";

        const html = `
            <div class="row mt-2" data-provider-id="${id}">
                <div class="col-4"><p>Price</p><p>₦ <span id="price">${order_amount}</span></p></div>
                <div class="col-3"></div>
                <div class="col-5"><p>Success Rate</p><p class="${success_rate_class}" id="success_rate">${success_rate}%</p></div>
                ${pool_codename === "Alpha" ? `
                    <div class="input-group mb-0 flex-column flex-md-row">
                        <div class="d-flex w-100">
                            <div class="input-group-prepend"><label class="input-group-text" for="area_code">Area codes</label></div>
                            <input type="text" class="form-control" name="area_code" placeholder="503, 202, 404">
                        </div>
                        <p class="text-xs opacity-60 py-1 px-2 w-100 mt-2 mt-md-0">Preferred area codes. Increases price by ${PRICE_INCREASE_PERCENTAGE}%.</p>
                    </div>
                    <div class="input-group mb-0 flex-column flex-md-row">
                        <div class="d-flex w-100">
                            <div class="input-group-prepend"><label class="input-group-text" for="carriers">Carriers</label></div>
                            <input type="text" class="form-control" name="carriers" placeholder="tmo, vz, att">
                        </div>
                        <p class="text-xs opacity-60 py-1 px-2 w-100 mt-2 mt-md-0">Preferred carrier. Increases price by ${PRICE_INCREASE_PERCENTAGE}%.</p>
                    </div>
                    <div class="input-group mb-0 flex-column flex-md-row">
                        <div class="d-flex w-100">
                            <div class="input-group-prepend"><label class="input-group-text" for="phone">Phone</label></div>
                            <input type="text" class="form-control" name="phone" placeholder="1112223333">
                        </div>
                        <p class="text-xs opacity-60 py-1 px-2 w-100 mt-2 mt-md-0">Preferred phone. Increases price by ${PRICE_INCREASE_PERCENTAGE}%.</p>
                    </div>
                ` : ''}
                <button class="btn btn-primary w-100 order-number-btn ${order_number_class}"
                    type="button" data-id="${pool_codename}" id="order_number_${id}"
                    onclick="order_number(event, '${pool_codename}', ${order_amount}, '${carrier}')">
                    Order Number <i class="bi bi-sim"></i>
                </button>
                <a href="/fund-wallet" id="fund_wallet_${id}" class="btn btn-primary text-white ${fund_wallet_class}">Fund Wallet</a>
            </div>
        `;
        $("#Service_info").append(html);
    });
};

let jsonData = []; // Global variable to store jsonData for polling
let stopPolling = null; // To store the polling stop function

const order_number = async (event, pool, max_price, card_carrier = "") => {
    $('.order-number-btn').prop('disabled', true);

    try {
        const area_code = $('input[name="area_code"]').val() || "";
        // Two carrier sources:
        //   1. card_carrier — passed in from the price card (Echo/Charlie pools
        //      where the parent returns the carrier as part of the price row).
        //   2. <input name="carriers"> — only rendered for Alpha (DaisySMS) as
        //      a free-text hint. If the user typed in it, prefer that.
        // The form input has priority because it represents an explicit choice
        // the user just made; card_carrier is the implicit per-row default.
        const carriers = ($('input[name="carriers"]').val() || "").trim() || card_carrier;
        const phone = $('input[name="phone"]').val() || "";

        const response = await $.ajax({
            url: `${baseUrl}/api/getNumber?api_key=${api_key}&service=${services_val}&country=${country_val}&pool=${pool}&max_price=${max_price}&areas=${area_code}&carriers=${encodeURIComponent(carriers)}&number=${phone}`,
            type: "GET",
            dataType: "json"
        });
        console.log('order_number response:', response);

        if (response === "NO_MONEY") {
            notyf.open({ type: "error", message: "Insufficient Balance" });
        } else if (response === "NO_NUMBERS") {
            notyf.open({ type: "warning", message: "No numbers available" });
        } else if (response.id) {
            // Show success notification
            notyf.open({ type: "success", message: "Number successfully ordered" });
            const balanceElement = document.getElementById("wallet_balance");
            if (balanceElement) balanceElement.textContent = response.balance || 0
            service_information.classList.add("d-none");
            // Reload table and update polling
            await loadHistory(); // This will refresh jsonData and restart polling
        } else {
            throw new Error("Unexpected response format");
        }
    } catch (error) {
        console.error('order_number error:', error);
        notyf.open({ type: "error", message: "Failed to order number: " + error.message });
    } finally {
        $('.order-number-btn').prop('disabled', false);
    }
};

// Table Initialization
const table = $('#order-table').DataTable({
    responsive: true,
    ordering: true,
    paging: true,
    searching: true,
    info: true,
    lengthChange: true,
    columns: [
        { data: 'id', title: 'ID' },
        { data: 'phone_number', title: 'Phone Number' },
        {
            data: 'code',
            title: 'Code',
            render: function(data, type, row) {
                if (typeof data === 'string' && data.startsWith('[')) {
                    try {
                        data = JSON.parse(data);
                    } catch (e) {
                        console.error('Failed to parse code:', data, e);
                    }
                }
                if (Array.isArray(data) && data.length > 0) {
                    return data.map(code => `<div>${code}</div>`).join('');
                    // Alternative: return data.join('<br>');
                }
                return data || '';
            }
        },
        { data: 'country', title: 'Country' },
        { data: 'service', title: 'Service' },
        { data: 'status', title: 'Status' },
        { data: 'price', title: 'Price' },
        {
            data: 'expiration_time',
            title: 'Time Remaining',
            render: function(data, type, row) {
                return data ? `<span class="countdown" data-expiration="${data}"></span>` : 'N/A';
            }
        },
        { data: 'actions', title: 'Actions' }
    ],
    order: [[0, 'desc']],
    drawCallback: function() {
        updateCountdowns();
    }
});

// Countdown Function
function updateCountdowns() {
    $('.countdown').each(function() {
        const $this = $(this);
        const $row = $this.closest('tr'); // Get the parent row
        const statusSpan = $row.find('td:eq(5) span'); // Status is in the 6th column (index 5)
        const status = statusSpan.attr('title'); // Get the status from the title attribute

        if (status !== 'Received') {
            return;
        }

        const expirationTime = $this.data('expiration');
        if (!expirationTime) {
            $this.text('N/A');
            return;
        }

        const timeRemaining = calculateTime(expirationTime);
        $this.text(timeRemaining === 'Time has passed' ? 'Expired' : `${timeRemaining.minutes}m ${timeRemaining.seconds}s`)
             .toggleClass('text-danger', timeRemaining === 'Time has passed');
       if (timeRemaining === 'Time has passed'){
            if (stopPolling) stopPolling(); // Stop previous polling
            loadHistory();
       }
    });
}

// Load History Function
const loadHistory = async () => {
    try {
        const response = await $.ajax({
            url: '/get_history',
            type: 'GET',
            dataType: 'json'
        });

        if (response.error) {
            if (response.error === 'Login Required') {
                window.location.replace("/login");
            }
            throw new Error(response.error);
        }

        if (!response.history || !Array.isArray(response.history)) {
            throw new Error('Invalid history data format');
        }

        table.clear();

        jsonData = response.history.map((record, index) => {
            const actionButtons = [
                record.repeatable === '1' && record.status === 'Received' && record.code ?
                    `<button class="btn btn-sm btn-primary get-more-code" data-id="${record.id}">Get More Code</button>` : '',
                record.status === 'Received' && !record.code ?
                    `<button class="btn btn-sm btn-danger cancel-activation" data-id="${record.id}">Cancel</button>` : '',
                record.code && record.status === 'Received' ?
                    `<button class="btn btn-sm btn-success finish-activation" data-id="${record.id}">Finish</button>` : ''
            ].filter(Boolean).join(' ');

            const rowData = {
                id: record.id || `unknown-${index}`,
                phone_number: record.phone_number || 'N/A',
                code: record.code || '',
                country: record.country || 'N/A',
                service: record.service || 'N/A',
                status: record.status ?
                    `<span title="${record.status}" data-expiration="${record.expiration_time}">${record.status}</span>` : 'N/A',
                price: record.price || '0.00',
                expiration_time: record.expiration_time || null,
                actions: actionButtons
            };

            const rowNode = table.row.add(rowData).node();
            $(rowNode).attr('data-history', JSON.stringify({
                expiration_time: record.expiration_time,
                duration: record.duration,
                source: record.source,
                check_status: record.check_status,
                repeatable: record.repeatable,
                activation_id: record.activation_id
            }));

            return rowData;
        });

        table.draw();
        document.getElementById("dt-search-0")?.classList.add("mb-3");

        // Stop existing polling if it exists
        if (stopPolling) stopPolling();

        const countdownInterval = setInterval(updateCountdowns, 1000);
        stopPolling = pollOrders(table, sound, jsonData);

        table.on('destroy', () => clearInterval(countdownInterval));

    } catch (error) {
        console.error('Error loading history:', error);
        notyf.open({ type: "error", message: "Failed to load order history: " + error.message });
    }
};

// Polling Functions
const checkOrderUpdates = async (table, sound, orderId, pollingInterval = POLLING_INTERVAL) => {
    try {
        const response = await $.get(`${API_BASE_URL}/api/getStatus?api_key=${api_key}&id=${orderId}`);
        if (response.status === "Received" && !response.sms) {
            return setTimeout(() => checkOrderUpdates(table, sound, orderId, pollingInterval), pollingInterval);
        } else if (response.status === "Received" && response.sms) {
            if (stopPolling) stopPolling(); // Stop previous polling
            loadHistory();
            sound.play().catch(err => console.error('Audio play error:', err));
            return null;
        }
        return null;
    } catch (error) {
        console.error(`checkOrderUpdates error for ${orderId}:`, error);
        return setTimeout(() => checkOrderUpdates(table, sound, orderId, pollingInterval), pollingInterval * 2);
    }
};

const pollOrders = (table, sound, jsonData) => {
    if (!Array.isArray(jsonData)) {
        console.error('pollOrders: jsonData is not an array:', jsonData);
        return () => {};
    }

    const activePolls = new Map();

    const pollSingleOrder = async (order) => {
        const orderId = order.id;
        const orderStatus = $(order.status).attr("title");

        if (orderStatus !== "Received" || !orderId || activePolls.has(orderId)) return;

        try {
            const dataExpiration = $(order.status).attr("data-expiration");
            const response = await $.get(`${API_BASE_URL}/api/getStatus?api_key=${api_key}&id=${orderId}`);

            if (dataExpiration && calculateTime(dataExpiration) === "Time has passed") {
                const balanceElement = document.getElementById("wallet_balance");
                if (balanceElement) balanceElement.textContent = response.balance || 0;
                if (stopPolling) stopPolling(); // Stop previous polling
                loadHistory();
                return;
            }

            if (response.status === "Received" && (!response.sms || response.check_status === true)) {
                const pollTimer = await checkOrderUpdates(table, sound, orderId);
                if (pollTimer) activePolls.set(orderId, pollTimer);
            }
        } catch (error) {
            console.error(`pollSingleOrder error for ${orderId}:`, error);
        }
    };

    const pollAll = async () => {
        await Promise.all(jsonData.map(pollSingleOrder));
        setTimeout(pollAll, POLLING_INTERVAL);
    };

    pollAll();
    return () => activePolls.forEach(timer => clearTimeout(timer));
};

// Document Ready
$(document).ready(() => {
    try {
        $('.select_object').select2();
    } catch (error) {
        console.error('Select2 initialization error:', error);
    }

    loadHistory();

    // Event Handlers
    $('#order-table').on('click', '.get-more-code', function() {
        const historyId = $(this).data('id');
        const row = table.row($(this).closest('tr'));
        if (row.index() === null) {
            console.error(`Row for historyId ${historyId} not found`);
            return;
        }
        const rowData = row.data();
        const historyData = JSON.parse($(row.node()).attr('data-history') || '{}');
        console.log('Get More Code:', { historyId, rowData, historyData });

        // Call getMoreCode with order ID, button element, and table
        getMoreCode(historyId, this, table);
    });

    // Event Handler for Cancel Activation
    $('#order-table').on('click', '.cancel-activation', function() {
        const historyId = $(this).data('id');
        const row = table.row($(this).closest('tr'));
        if (row.index() === null) {
            console.error(`Row for historyId ${historyId} not found`);
            return;
        }
        const rowData = row.data();
        console.log('Cancel Activation:', { historyId, rowData });

        // Call cancelOrder with the order ID, row, and button element
        cancelOrder(historyId, row, this);
    });

    $('#order-table').on('click', '.finish-activation', function() {
        const historyId = $(this).data('id');
        const row = table.row($(this).closest('tr'));
        if (row.index() === null) {
            console.error(`Row for historyId ${historyId} not found`);
            return;
        }
        const rowData = row.data();
        console.log('Finish Activation:', { historyId, rowData });
        // Add finish logic here if needed
        finishOrder(historyId, row);
    });

});