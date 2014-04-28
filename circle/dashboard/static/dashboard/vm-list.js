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

  $('.vm-list-table tbody').find('tr').mousedown(function() {
    var retval = true;
    if (ctrlDown) {
      setRowColor($(this));
      if(!$(this).hasClass('vm-list-selected')) {
        selected.splice(getSelectedIndex($(this).index()), 1);
      } else {
        selected.push({'index': $(this).index(), 'vm': $(this).data("vm-pk")});
      }
      retval = false;
    } else if(shiftDown) {
      if(selected.length > 0) {
        start = selected[selected.length - 1]['index'] + 1;
        end = $(this).index();

        if(start > end) {
          var tmp = start - 1; start = end; end = tmp - 1;
        }

        for(var i = start; i <= end; i++) {
          var vm = $(".vm-list-table tbody tr").eq(i).data("vm-pk");
          if(!isAlreadySelected(vm)) {
            selected.push({'index': i, 'vm': vm});
            setRowColor($('.vm-list-table tbody tr').eq(i));
            }
        }
      }
      retval = false;
    } else {
      $('.vm-list-selected').removeClass('vm-list-selected');
      $(this).addClass('vm-list-selected');
      selected = [{'index': $(this).index(), 'vm': $(this).data("vm-pk")}];
    }

    // reset btn disables
    $('.vm-list-table tbody tr .btn').attr('disabled', false);
    // show/hide group controls
    if(selected.length > 1) {
      $('.vm-list-group-control a').attr('disabled', false);
      for(var i = 0; i < selected.length; i++) {
        $('.vm-list-table tbody tr').eq(selected[i]).find('.btn').attr('disabled', true);
      }
    } else {
      $('.vm-list-group-control a').attr('disabled', true);
    }
    return retval;
  });

    
  $('#vm-list-group-migrate').click(function() {
    // pass?
  });

  $('.vm-list-details').popover({
    'placement': 'auto',
    'html': true,
    'trigger': 'hover'
  });

  $('.vm-list-connect').popover({
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

  /* rename */
  $("#vm-list-rename-button, .vm-details-rename-button").click(function() {
    $("#vm-list-column-name", $(this).closest("tr")).hide();
    $("#vm-list-rename", $(this).closest("tr")).css('display', 'inline');
    $("#vm-list-rename-name", $(this).closest("tr")).focus();
  });

  /* rename ajax */
  $('.vm-list-rename-submit').click(function() {
    var row = $(this).closest("tr")
    var name = $('#vm-list-rename-name', row).val();
    var url = '/dashboard/vm/' + row.children("td:first-child").text().replace(" ", "") + '/';
    $.ajax({
      method: 'POST',
      url: url,
      data: {'new_name': name},
      headers: {"X-CSRFToken": getCookie('csrftoken')},
      success: function(data, textStatus, xhr) {
        
        $("#vm-list-column-name", row).html(
          $("<a/>", {
            'class': "real-link",
            href: "/dashboard/vm/" + data['vm_pk'] + "/",
            text: data['new_name']
          })
        ).show();
        $('#vm-list-rename', row).hide();
        // addMessage(data['message'], "success");
      },
      error: function(xhr, textStatus, error) {
        addMessage("Error during renaming!", "danger");
      }
    });
    return false;
  });
  
  
  /* group actions */

  /* select all */
  $('#vm-list-group-select-all').click(function() {
    $('.vm-list-table tbody tr').each(function() {
      var index = $(this).index();
      var vm = $(this).data("vm-pk");
      if(!isAlreadySelected(vm)) {
        selected.push({'index': index, 'vm': vm});
        $(this).addClass('vm-list-selected');
      }
    });
    if(selected.length > 0)
      $('.vm-list-group-control a').attr('disabled', false);
    return false;
  });

  /* mass vm delete */
  $('#vm-list-group-delete').click(function() {
    addModalConfirmation(massDeleteVm,
      {
        'url': '/dashboard/vm/mass-delete/',
        'data': {
          'selected': selected,
          'v': collectIds(selected)
        }
      }
    );
    return false;
  });

  /* table sort */
  var table = $(".vm-list-table").stupidtable();

  table.on("beforetablesort", function(event, data) {
    return false;
  });

  table.on("aftertablesort", function(event, data) {
    // this didn't work ;;
    // var th = $("this").find("th");
    
    $(".vm-list-table thead th i").remove();

    var icon_html = '<i class="icon-sort-' + (data.direction == "desc" ? "up" : "down") + ' pull-right"></i>';
    $(".vm-list-table thead th").eq(data.column).append(icon_html);
  });

  //$(".vm-list-table thead th a").attr("href", "#");
  // only if js is enabled
  $(".vm-list-table thead th").css("cursor", "pointer");
});

function isAlreadySelected(vm) {
  for(var i=0; i<selected.length; i++)
    if(selected[i].vm == vm)
      return true;
  return false;
}

function getSelectedIndex(index) {
  for(var i=0; i<selected.length; i++)
    if(selected[i].index == index)
      return i;
  return -1;
}

function collectIds(rows) {
  var ids = [];
  for(var i = 0; i < rows.length; i++) {
    ids.push(rows[i].vm);
  }
  return ids;  
}

function setRowColor(row) {
  if(!row.hasClass('vm-list-selected')) {
    row.addClass('vm-list-selected');
  } else {
    row.removeClass('vm-list-selected');
  }
}
