$(function() {
  /* for template removes buttons */
  $('.template-delete').click(function() {
    var template_pk = $(this).data('template-pk');
    addModalConfirmation(deleteTemplate,
      { 'url': '/dashboard/template/delete/' + template_pk + '/',
        'data': [],
        'template_pk': template_pk,
      });
    return false;
  });

  /* for lease removes buttons */
  $('.lease-delete').click(function() {
    var lease_pk = $(this).data('lease-pk');
    addModalConfirmation(deleteLease,
      { 'url': '/dashboard/lease/delete/' + lease_pk + '/',
        'data': [],
        'lease_pk': lease_pk,
    });
    return false;
  });
});


// send POST request then delete the row in table
function deleteTemplate(data) {
  $.ajax({
    type: 'POST',
    url: data['url'],
    headers: {"X-CSRFToken": getCookie('csrftoken')}, 
    success: function(re, textStatus, xhr) { 
      addMessage(re['message'], 'success');
      $('a[data-template-pk="' + data['template_pk'] + '"]').closest('tr').fadeOut(function() {
        $(this).remove();
      });
    },
    error: function(xhr, textStatus, error) {
      addMessage('Uh oh :(', 'danger')
    }
  });
}


// send POST request then delete the row in table
function deleteLease(data) {
  $.ajax({
    type: 'POST',
    url: data['url'],
    headers: {"X-CSRFToken": getCookie('csrftoken')}, 
    success: function(re, textStatus, xhr) { 
      addMessage(re['message'], 'success');
      $('a[data-lease-pk="' + data['lease_pk'] + '"]').closest('tr').fadeOut(function() {
        $(this).remove();
      });
    },
    error: function(xhr, textStatus, error) {
      addMessage('Uh oh :(', 'danger')
    }
  });
}