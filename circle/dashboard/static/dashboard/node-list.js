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

  $('.node-list-table tbody').find('tr').mousedown(function() {
    if (ctrlDown) {
      setRowColor($(this));
      if(!$(this).hasClass('node-list-selected')) {
        selected.splice(selected.indexOf($(this).index()), 1);
      } else {
        selected.push($(this).index());
      }
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
            setRowColor($('.node-list-table tbody tr').eq(i));
            }
        }
      }
    } else {
      $('.node-list-selected').removeClass('node-list-selected');
      $(this).addClass('node-list-selected');
      selected = [$(this).index()];
    }

    // reset btn disables
    $('.node-list-table tbody tr .btn').attr('disabled', false);
    // show/hide group controls
    if(selected.length > 1) {
      $('.node-list-group-control a').attr('disabled', false);
      for(var i = 0; i < selected.length; i++) {
        $('.node-list-table tbody tr').eq(selected[i]).find('.btn').attr('disabled', true);
      }
    } else {
      $('.node-list-group-control a').attr('disabled', true);
    }
    return false;
  });

    
  $('#node-list-group-migrate').click(function() {
    console.log(collectIds(selected));
  });

  $('.node-list-details').popover({
    'placement': 'auto',
    'html': true,
    'trigger': 'hover'
  });

  $('.node-list-connect').popover({
    'placement': 'left',
    'html': true,
    'trigger': 'click'
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

  /* group actions */

  /* select all */
  $('#node-list-group-select-all').click(function() {
    $('.node-list-table tbody tr').each(function() {
      var index = $(this).index();
      if(selected.indexOf(index) < 0) {
        selected.push(index);
        $(this).addClass('node-list-selected');
      }
    });
    if(selected.length > 0)
      $('.node-list-group-control a').attr('disabled', false);
    return false;
  });

  /* mass vm delete */
  $('#node-list-group-delete').click(function() {
    text = "Are you sure you want to delete the selected VMs?";
    random_vm_pk = $('.vm-delete').eq(0).data('vm-pk');
    addModalConfirmation(text, random_vm_pk, massDeleteVm, false);
    return false;
  });
});

function collectIds(rows) {
  var ids = [];
  for(var i = 0; i < rows.length; i++) {
    var div = $('td:first-child div', $('.node-list-table tbody tr').eq(rows[i]));
    ids.push(div.prop('id').replace('vm-', ''));
  }
  return ids;  
}

function setRowColor(row) {
  if(!row.hasClass('vm-list-selected')) {
    row.addClass('node-list-selected');
  } else {
    row.removeClass('node-list-selected');
  }

}
