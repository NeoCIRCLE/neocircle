var ctrlDown, shiftDown = false;
var ctrlKey = 17;
var shiftKey = 16;
var selected = [];

$(function() {
  $(document).keydown(function(e) {
    if (e.keyCode == ctrlKey) ctrlDown = true;
    if (e.keyCode == shiftKey) shiftDown = true;
  }).keyup(function(e) {
    if (e.keyCode == ctrlKey) ctrlDown = false;
    if (e.keyCode == shiftKey) shiftDown = false;
  });

  $('.group-list-table tbody').find('tr').mousedown(function() {
    var retval = true;
    if (ctrlDown) {
      setRowColor($(this));
      if(!$(this).hasClass('group-list-selected')) {
        selected.splice(selected.indexOf($(this).index()), 1);
      } else {
        selected.push($(this).index());
      }
      retval = false;
    } else if(shiftDown) {
      if(selected.length > 0) {
        start = selected[selected.length - 1] + 1;
        end = $(this).index();

        if(start > end) {
          var tmp = start - 1; start = end; end = tmp - 1;
        }

        for(var i = start; i <= end; i++) {
          if(selected.indexOf(i) < 0) {
            selected.push(i);
            setRowColor($('.group-list-table tbody tr').eq(i));
            }
        }
      }
      retval = false;
    } else {
      $('.group-list-selected').removeClass('group-list-selected');
      $(this).addClass('group-list-selected');
      selected = [$(this).index()];
    }

    // reset btn disables
    $('.group-list-table tbody tr .btn').attr('disabled', false);
    // show/hide group controls
    if(selected.length > 1) {
      $('.group-list-group-control a').attr('disabled', false);
      for(var i = 0; i < selected.length; i++) {
        $('.group-list-table tbody tr').eq(selected[i]).find('.btn').attr('disabled', true);
      }
    } else {
      $('.group-list-group-control a').attr('disabled', true);
    }
    return retval;
  });

  $('#group-list-group-migrate').click(function() {
    console.log(collectIds(selected));
  });


  $('tbody a').mousedown(function(e) {
    // parent tr doesn't get selected when clicked
    e.stopPropagation();
    });

  $('tbody a').click(function(e) {
    // browser doesn't jump to top when clicked the buttons
      
      if(!$(this).hasClass('real-link')) {
      return false;
    }
  });

  
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
            href: "/dashboard/group/" + data['node_pk'] + "/",
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


  /* group actions */

  /* select all */
  $('#group-list-group-select-all').click(function() {
    $('.group-list-table tbody tr').each(function() {
      var index = $(this).index();
      if(selected.indexOf(index) < 0) {
        selected.push(index);
        $(this).addClass('group-list-selected');
      }
    });
    if(selected.length > 0)
      $('.group-list-group-control a').attr('disabled', false);
    return false;
  });

  /* mass vm delete */
  $('#group-list-group-delete').click(function() {
    addModalConfirmation(massDeleteVm,
      {
        'url': '/dashboard/group/mass-delete/',
        'data': {
          'selected': selected,
          'v': collectIds(selected)
        }
      }
    );
    return false;
  });
});

function collectIds(rows) {
  var ids = [];
  for(var i = 0; i < rows.length; i++) {
    var div = $('td:first-child div', $('.group-list-table tbody tr').eq(rows[i]));
    ids.push(div.prop('id').replace('node-', ''));
  }
  return ids;  
}

function setRowColor(row) {
  if(!row.hasClass('group-list-selected')) {
    row.addClass('group-list-selected');
  } else {
    row.removeClass('group-list-selected');
  }
}
