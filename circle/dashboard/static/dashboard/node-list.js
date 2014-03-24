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
    var retval = true;
    if (ctrlDown) {
      setRowColor($(this));
      if(!$(this).hasClass('node-list-selected')) {
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
            setRowColor($('.node-list-table tbody tr').eq(i));
            }
        }
      }
      retval = false;
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
    return retval;
  });

  $('#node-list-group-migrate').click(function() {
    console.log(collectIds(selected));
  });

  $(document).ready( function()
  {
    colortable();
    $('.node-list-details').popover(
    {
      placement : 'auto',
      html : true,
      trigger : 'click',
    });
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

  // find disabled nodes, set danger (red) on the rows
  function colortable() 
  {
	var tr= $('.false').closest("tr");
	tr.addClass('danger');
	var tr= $('.true').closest("tr");
	tr.removeClass('danger');
  }

  /* rename */
  $("#node-list-rename-button, .node-details-rename-button").click(function() {
    $("#node-list-column-name", $(this).closest("tr")).hide();
    $("#node-list-rename", $(this).closest("tr")).css('display', 'inline');
  });

  /* rename ajax */
  $('.node-list-rename-submit').click(function() {
    var row = $(this).closest("tr")
    var name = $('#node-list-rename-name', row).val();
    var url = '/dashboard/node/' + row.children("td:first-child").text().replace(" ", "") + '/';
    $.ajax({
      method: 'POST',
      url: url,
      data: {'new_name': name},
      headers: {"X-CSRFToken": getCookie('csrftoken')},
      success: function(data, textStatus, xhr) {
        
        $("#node-list-column-name", row).html(
          $("<a/>", {
            'class': "real-link",
            href: "/dashboard/node/" + data['node_pk'] + "/",
            text: data['new_name']
          })
        ).show();
        $('#node-list-rename', row).hide();
        // addMessage(data['message'], "success");
      },
      error: function(xhr, textStatus, error) {
	 addMessage("Error during renaming!", "danger");
      }
    });
    return false;
  });

  function statuschangeSuccess(tr){
   var tspan=tr.children('.enabled').children();
    var buttons=tr.children('.actions').children('.btn-group').children('.dropdown-menu').children('li').children('.node-enable');
 
    buttons.each(function(index){
      if ($(this).css("display")=="block"){
          $(this).css("display","none");
        }
      else{
         $(this).css("display","block");
        }
    }); 
    if(tspan.hasClass("false")){
          tspan.removeClass("false");
	  tspan.addClass("true");
 	  tspan.text("✔");
      } 
  else{
  	  tspan.removeClass("true");
	  tspan.addClass("false");
	  tspan.text("✘");
      }
  	  colortable();
  }


  $('#table_container').on('click','.node-enable',function() {
    var tr= $(this).closest("tr");
    var pk =$(this).attr('data-node-pk');
    var url = '/dashboard/node/' + pk  + '/';
    $.ajax({
      method: 'POST',
      url: url,
      data: {'change_status':''},
      headers: {"X-CSRFToken": getCookie('csrftoken')},
      success: function(data, textStatus, xhr) {
      statuschangeSuccess(tr);
      },
      error: function(xhr, textStatus, error) {
        addMessage("Error!", "danger");
      }
    });
    return false;
  });


  // enabling / disabling node
  function enablenode(pk,new_status,onsuccess,params) {
  }



// refresh the given contents, parameter is the array of contents, in pair
  function contentrefresh(elements,callbacks){
  for (var i = 0; i < elements.length; i+=2) {
      $(elements[i]).load(location.href+" "+elements[i+1],callbacks[i/2]);
  }

  }

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
    addModalConfirmation(massDeleteVm,
      {
        'url': '/dashboard/node/mass-delete/',
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
    var div = $('td:first-child div', $('.node-list-table tbody tr').eq(rows[i]));
    ids.push(div.prop('id').replace('node-', ''));
  }
  return ids;  
}

function setRowColor(row) {
  if(!row.hasClass('node-list-selected')) {
    row.addClass('node-list-selected');
  } else {
    row.removeClass('node-list-selected');
  }
}
