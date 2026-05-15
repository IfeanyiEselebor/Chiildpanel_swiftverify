$(document).ready(function() {
      /* Initiate Datatables */
  var table = $('#transaction').DataTable({
    responsive: true,
    ajax: {
      type: "GET",
      url: '/load-transaction',
      dataSrc: function(json) {
        // Check if the response was successful
        if (json.data['status'] === "Login Required") {
          /* Reload Page */
          location.reload();
        } else {
          return json.data;
        }
      }
    },

    columns: [
      { data: 'id' },
      { data: 'date' },
      { data: 'operation' },
      { data: 'amount' },
      { data: 'status' },
      { data: 'balance' }
    ],
    order: [[1, "desc"]]
  });
})