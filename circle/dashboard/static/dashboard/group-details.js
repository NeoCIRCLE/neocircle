
  /* rename */
  $("#group-details-h1-name, .group-details-rename-button").click(function() {
    $("#group-details-h1-name").hide();
    $("#group-details-rename").css('display', 'inline');
    $("#group-details-rename-name").focus();
  });

  /* rename ajax */
  $('#group-details-rename-submit').click(function() {
    var name = $('#group-details-rename-name').val();
    $.ajax({
      method: 'POST',
      url: location.href,
      data: {'new_name': name},
      headers: {"X-CSRFToken": getCookie('csrftoken')},
      success: function(data, textStatus, xhr) {
        $("#group-details-h1-name").html(data['new_name']).show();
        $('#group-details-rename').hide();
        // addMessage(data['message'], "success");
      },
      error: function(xhr, textStatus, error) {
        addMessage("Error during renaming!", "danger");
      }
    });
    return false;
  });
