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
    event.preventDefault();
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
