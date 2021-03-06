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
    if(!$(this).data("vm-pk")) return;
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
        start = selected[selected.length - 1].index + 1;
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

    // show/hide group controls
    if(selected.length > 0) {
      $('#vm-mass-ops .mass-operation').attr('disabled', false);
    } else {
      $('#vm-mass-ops .mass-operation').attr('disabled', true);
    }
    return retval;
  });

  $('tbody a').mousedown(function(e) {
    // parent tr doesn't get selected when clicked
    e.stopPropagation();
    });

  /* group actions */

  /* select all */
  $('#vm-list-group-select-all').click(function() {
    $('.vm-list-table tbody tr').each(function() {
      var index = $(this).index();
      var vm = $(this).data("vm-pk");
      if(vm && !isAlreadySelected(vm)) {
        selected.push({'index': index, 'vm': vm});
        $(this).addClass('vm-list-selected');
      }
    });
    if(selected.length > 0)
      $('#vm-mass-ops .mass-operation').attr('disabled', false);
    return false;
  });


  /* mass operations */
  $("#vm-mass-ops").on('click', '.mass-operation', function(e) {
    var icon = $(this).children("i").addClass('fa-spinner fa-spin');
    params = "?" + selected.map(function(a){return "vm=" + a.vm;}).join("&");

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


  $("body").on("click", "#mass-op-form-send", function() {
    var url = $(this).closest("form").prop("action");
    $(this).find("i").prop("class", "fa fa-fw fa-spinner fa-spin");

    $.ajax({
      url: url,
      headers: {"X-CSRFToken": getCookie('csrftoken')},
      type: 'POST',
      data: $(this).closest('form').serialize(),
      success: function(data, textStatus, xhr) {
        /* hide the modal we just submitted */
        $('#confirmation-modal').modal("hide");

        updateStatuses(1);

        /* if there are messages display them */
        if(data.messages && data.messages.length > 0) {
          addMessage(data.messages.join("<br />"), "danger");
        }
      },
      error: function(xhr, textStatus, error) {
        $('#confirmation-modal').modal("hide");

        if (xhr.status == 500) {
          addMessage("500 Internal Server Error", "danger");
        } else {
          addMessage(xhr.status + " " + xhr.statusText, "danger");
        }
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

  $(document).on("click", ".mass-migrate-node", function() {
    $(this).find('input[type="radio"]').prop("checked", true);
  });

  if(checkStatusUpdate() || $("#vm-list-table tbody tr").length >= 100) {
    updateStatuses(1);
  }

});


function checkStatusUpdate() {
  icons = $("#vm-list-table tbody td.state i");
  if(icons.hasClass("fa-spin") || icons.hasClass("migrating-icon")) {
    return true;
  }
}


function updateStatuses(runs) {
  var include_deleted = getParameterByName("include_deleted");
  $.get("/dashboard/vm/list/?compact", function(result) {
    $("#vm-list-table tbody tr").each(function() {
      vm = $(this).data("vm-pk");
      status_td = $(this).find("td.state");
      status_icon = status_td.find("i");
      status_text = status_td.find("span");

      if(vm in result) {
        if(result[vm].in_status_change) {
          if(!status_icon.hasClass("fa-spin")) {
            status_icon.prop("class", "fa fa-fw fa-spinner fa-spin");
          }
        }
        else if(result[vm].status == "MIGRATING") {
          if(!status_icon.hasClass("migrating-icon")) {
            status_icon.prop("class", "fa fa-fw " + result[vm].icon + " migrating-icon");
          }
        } else {
          status_icon.prop("class", "fa fa-fw " + result[vm].icon);
        }
        status_text.text(result[vm].status);
        if("node" in result[vm]) {
          $(this).find(".node").text(result[vm].node);
        }
      } else {
        if(!include_deleted)
          $(this).remove();
      }
    });

    if(checkStatusUpdate()) {
      setTimeout(
          function() {updateStatuses(runs + 1);},
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
