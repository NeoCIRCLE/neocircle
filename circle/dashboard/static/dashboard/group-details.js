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

  /* for Node removes buttons */
  $('.delete-from-group').click(function() {
    var href = $(this).attr('href');
    var tr = $(this).closest('tr');
    var group = $(this).data('group_pk');
    var member = $(this).data('member_pk');
    var dir = window.location.pathname.indexOf('list') == -1;
    addModalConfirmation(removeMember, 
      { 'url': href,
	'data': [],
	'tr': tr,
	'group_pk': group,
	'member_pk': member,
	'type': "user",
	'redirect': dir});

    return false;
  });

function removeMember(data) {
  $.ajax({
    type: 'POST',
    url: data['url'],
    headers: {"X-CSRFToken": getCookie('csrftoken')},
    success: function(re, textStatus, xhr) {
    data['tr'].fadeOut(function() {
	    $(this).remove();});
    },
    error: function(xhr, textStatus, error) {
      addMessage('Uh oh :(', 'danger')
    }
  });
}


