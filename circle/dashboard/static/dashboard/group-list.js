$(function() {
  /* rename */
  $("#group-list-rename-button, .group-details-rename-button").click(function() {
    $("#group-list-column-name", $(this).closest("tr")).hide();
    $("#group-list-rename", $(this).closest("tr")).css('display', 'inline');
  });

  /* rename ajax */
  $('.group-list-rename-submit').click(function() {
    var row = $(this).closest("tr")
    var name = $('#group-list-rename-name', row).val();
    var url = '/dashboard/group/' + row.children("td:first-child").text().replace(" ", "") + '/';
    $.ajax({
      method: 'POST',
      url: url,
      data: {'new_name': name},
      headers: {"X-CSRFToken": getCookie('csrftoken')},
      success: function(data, textStatus, xhr) {
        
        $("#group-list-column-name", row).html(
          $("<a/>", {
            'class': "real-link",
            href: "/dashboard/group/" + data['group_pk'] + "/",
            text: data['new_name']
          })
        ).show();
        $('#group-list-rename', row).hide();
        // addMessage(data['message'], "success");
      },
      error: function(xhr, textStatus, error) {
	 addMessage("uhoh", "danger");
      }
    });
    return false;
  });

});
