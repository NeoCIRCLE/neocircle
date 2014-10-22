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
