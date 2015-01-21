$(function() {
  if($("#network-host-list-table").length) {
    var order = ["hostname", "vlan", "mac", "ipv4", "ipv6", "external_ipv4", "created_at", "owner"]
    var options = {
      paging: false,
        columnDefs: [
          { type: 'cloud-hostname', targets: 0},
          { type: 'ip-address', targets: [3,6]},
        ],
        language: {
          zeroRecords: gettext("No host found.")
        }
    }
    table = createDataTable($("#network-host-list-table"), options, "sort", order);

    $("#network-host-list-input").keyup(function() {
        table.search($(this).val()).draw();
      });
    $("#network-host-list-input").trigger("keyup");

    $("#network-host-list-table_filter, #network-host-list-table_info").remove();
  }
});


function createDataTable(table_element, options, sort_parameter_name, sort_order) {
  var table = $(table_element).DataTable(options);

  var sort = getParameterByName(sort_parameter_name);

  var dir = "asc";
  var index = 0;
  if(sort.length > 0 && sort[0] == "-") {
    dir = "desc"
    sort = sort.substr(1, sort.length - 1);
  }
  if(sort)
    index = sort_order.indexOf(sort);

  table.order([[index, dir]]);
  return table;
}
