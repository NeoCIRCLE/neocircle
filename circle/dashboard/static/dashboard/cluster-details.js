$(function() {
  /* rename */
  $("#cluster-details-h1-name, .cluster-details-rename-button").click(function() {
    $("#cluster-details-h1-name span").hide();
    $("#cluster-details-rename-form").show().css('display', 'inline-block');
    $("#cluster-details-rename-name").select();
  });

  /* rename ajax */
  $('#cluster-details-rename-submit').click(function() {
    if(!$("#cluster-details-rename-name")[0].checkValidity()) {
      return true;
    }
    var name = $('#cluster-details-rename-name').val();

    $.ajax({
      method: 'POST',
      url: location.href,
      data: {'new_name': name},
      headers: {"X-CSRFToken": getCookie('csrftoken')},
      success: function(data, textStatus, xhr) {
        $("#cluster-details-h1-name span").text(data.new_name).show();
        $('#cluster-details-rename-form').hide();
      },
      error: function(xhr, textStatus, error) {
        addMessage("Error during renaming.", "danger");
      }
    });
    return false;
  });
});
