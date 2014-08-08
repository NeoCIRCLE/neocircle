$(function() {
  $(document).ready( function() {
    colortable();
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
    var url = $(this).attr('href');
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
});
