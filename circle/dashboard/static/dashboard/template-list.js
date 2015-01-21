$(function() {
  /* template table sort */
  var ttable = $(".template-list-table").stupidtable();

  ttable.on("beforetablesort", function(event, data) {
    // pass
  });

  ttable.on("aftertablesort", function(event, data) {
    $(".template-list-table thead th i").remove();

    var icon_html = '<i class="fa fa-sort-' + (data.direction == "desc" ? "desc" : "asc") + ' pull-right" style="position: absolute;"></i>';
    $(".template-list-table thead th").eq(data.column).append(icon_html);
  });

  // only if js is enabled
  $(".template-list-table thead th").css("cursor", "pointer");

  $(".template-list-table th a").on("click", function(event) {
    if(!$(this).closest("th").data("sort")) return true;
    event.preventDefault();
  });
});
