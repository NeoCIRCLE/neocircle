$(function() {
  /* rename */
  $("#group-details-h1-name, .group-details-rename-button").click(function() {
    $("#group-details-h1-name span").hide();
    $("#group-details-rename-form").show().css('display', 'inline-block');
    $("#group-details-rename-name").select();
  });

  /* rename ajax */
  $('#group-details-rename-submit').click(function() {
    if(!$("#group-details-rename-name")[0].checkValidity()) {
      return true;
    }
    var name = $('#group-details-rename-name').val();

    $.ajax({
      method: 'POST',
      url: location.href,
      data: {'new_name': name},
      headers: {"X-CSRFToken": getCookie('csrftoken')},
      success: function(data, textStatus, xhr) {
        $("#group-details-h1-name span").text(data.new_name).show();
        $('#group-details-rename-form').hide();
      },
      error: function(xhr, textStatus, error) {
        addMessage("Error during renaming.", "danger");
      }
    });
    return false;
  });
});
