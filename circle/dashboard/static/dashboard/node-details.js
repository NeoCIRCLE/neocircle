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

  /* for Node removes buttons */
  $('.node-enable').click(function() {
    var node_pk = $(this).data('node-pk');
    var dir = window.location.pathname.indexOf('list') == -1;
    addModalConfirmation(changeNodeStatus, 
      { 'url': '/dashboard/node/status/' + node_pk + '/',
        'data': [],
        'pk': node_pk,
        'type': "node",
        'redirect': dir});

    return false;
  });

function changeNodeStatus(data) {
  $.ajax({
    type: 'POST',
    url: data['url'],
    headers: {"X-CSRFToken": getCookie('csrftoken')},
    success: function(re, textStatus, xhr) {
      if(!data['redirect']) {
        selected = [];
        addMessage(re['message'], 'success');
        $('a[data-'+data['type']+'-pk="' + data['pk'] + '"]').closest('tr').fadeOut(function() {
          $(this).remove();
        });
      } else {
        window.location.replace('/dashboard');
      }
    },
    error: function(xhr, textStatus, error) {
      addMessage('Uh oh :(', 'danger')
    }
  });
}

/* for Node flush buttons */
  $('.node-flush').click(function() {
    var node_pk = $(this).data('node-pk');
    var dir = window.location.pathname.indexOf('list') == -1;
    addModalConfirmation(changeNodeStatus, 
      { 'url': '/dashboard/node/flush/' + node_pk + '/',
        'data': [],
        'pk': node_pk,
        'type': "node",
        'redirect': dir});

    return false;
  });


  // remove trait
  $('.node-details-remove-trait').click(function() {
    var to_remove =  $(this).data("trait-pk");
    var clicked = $(this);
    $.ajax({
      type: 'POST',
      url: location.href,
      headers: {"X-CSRFToken": getCookie('csrftoken')}, 
      data: {'to_remove': to_remove},
      success: function(re) {
        if(re['message'].toLowerCase() == "success") {
          $(clicked).closest(".label").fadeOut(500, function() {
            $(this).remove();
          });
        }
      },
      error: function() {
        addMessage(re['message'], 'danger');
      }

    });
    return false;
  });
