$(function() {
  // change user avatar
  $("#dashboard-profile-use-gravatar").click(function() {
    var checked = $(this).prop("checked");
    var user = $(this).data("user");

    $.ajax({
      type: 'POST',
      url:"/dashboard/profile/" + user + "/use_gravatar/",
      headers: {"X-CSRFToken": getCookie('csrftoken')},
      success: function(re) {
        if(re.new_avatar_url) {
          $("#dashboard-profile-avatar").prop("src", re.new_avatar_url);
        }
      },
      error: function(xhr, textStatus, error) {
        if(xhr.status == 403) {
          addMessage(gettext("You have no permission to change this profile."), "danger");
        } else {
          addMessage(gettext("Unknown error."), "danger");
        }
      }
    });
  });
});

