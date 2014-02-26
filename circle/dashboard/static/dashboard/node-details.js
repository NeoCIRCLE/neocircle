
  /* rename */
  $("#node-details-h1-name, .node-details-rename-button").click(function() {
    $("#node-details-h1-name").hide();
    $("#node-details-rename").css('display', 'inline');
    $("#node-details-rename-name").focus();
  });

  /* rename ajax */
  $('#node-details-rename-submit').click(function() {
    var name = $('#node-details-rename-name').val();
    $.ajax({
      method: 'POST',
      url: location.href,
      data: {'new_name': name},
      headers: {"X-CSRFToken": getCookie('csrftoken')},
      success: function(data, textStatus, xhr) {
        $("#node-details-h1-name").html(data['new_name']).show();
        $('#node-details-rename').hide();
        // addMessage(data['message'], "success");
      },
      error: function(xhr, textStatus, error) {
        addMessage("Error during renaming!", "danger");
      }
    });
    return false;
  });
