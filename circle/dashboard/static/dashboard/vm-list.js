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
    if(selected.length > 0) {
      $('.vm-list-group-control a').attr('disabled', false);
      for(var i = 0; i < selected.length; i++) {
        $('.vm-list-table tbody tr').eq(selected[i]).find('.btn').attr('disabled', true);
      }
    } else {
      $('.vm-list-group-control a').attr('disabled', true);
    }
    return retval;
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


  /* mass operations */
  $("#vm-mass-ops").on('click', '.mass-operation', function(e) {
    var icon = $(this).children("i").addClass('fa-spinner fa-spin');
    params = "?a";
    for(var i=0; i<selected.length; i++) {
      params += "&vm=" + selected[i].vm;
    }

    $.ajax({
      type: 'GET',
      url: $(this).attr('href') + params,
      success: function(data) {
        icon.removeClass("fa-spinner fa-spin");
        $('body').append(data);
        $('#confirmation-modal').modal('show');
        $('#confirmation-modal').on('hidden.bs.modal', function() {
          $('#confirmation-modal').remove();
        });
        $("[title]").tooltip({'placement': "left"});
      }
    });
    return false;
  });

  /* table sort */
  var table = $(".vm-list-table").stupidtable();

  table.on("beforetablesort", function(event, data) {
    $(".table-sorting").show();
  });

  table.on("aftertablesort", function(event, data) {
    // this didn't work ;;
    // var th = $("this").find("th");
    $(".table-sorting").hide();
    
    $(".vm-list-table thead th i").remove();

    var icon_html = '<i class="fa fa-sort-' + (data.direction == "desc" ? "desc" : "asc") + ' pull-right"></i>';
    $(".vm-list-table thead th").eq(data.column).append(icon_html);
  });

  // only if js is enabled
  $(".vm-list-table thead th").css("cursor", "pointer");

  $(".vm-list-table th a").on("click", function(event) {
    event.preventDefault();
  });

  if(checkStatusUpdate()) {
    updateStatuses(1);
  }
});


function checkStatusUpdate() {
  if($("#vm-list-table tbody td.state i").hasClass("fa-spin")) {
    return true;
  }
}


function updateStatuses(runs) {
  $.get("/dashboard/vm/list/?compact", function(result) {
    $("#vm-list-table tbody tr").each(function() {
      vm = $(this).data("vm-pk");
      status_td = $(this).find("td.state");
      status_icon = status_td.find("i");
      status_text = status_td.find("span");

      if(vm in result) {
        if(result[vm].in_status_change) {
          if(!status_icon.hasClass("fa-spin")) {
            status_icon.prop("class", "fa fa-spinner fa-spin");
          }
        } else {
          status_icon.prop("class", "fa " + result[vm].icon);
        }
        status_text.text(result[vm].status);
      } else {
        $(this).remove();
      }
    });
    
    if(checkStatusUpdate()) {
      setTimeout(
          function() {updateStatuses(runs + 1)}, 
          1000 + Math.exp(runs * 0.05)
      );
    }
  });
}


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
