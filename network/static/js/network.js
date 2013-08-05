

$('i[class="icon-remove"]').click(function() {
    href = $(this).parent('a').attr('href');
    csrf = getCookie('csrftoken');
    
    var click_this = this;

    bootbox.dialog("Are you sure?", [
        {
            "label": "Cancel",
            "class": "btn-info",
            "callback": function () {}
        },
        {
            "label": "Remove",
            "class": "btn-danger",
            "callback": function() {
                delete_rule_or_group(click_this);
            }
        }
    ]);
    return false;
});


function delete_rule_or_group(click_this) {
    ajax = $.ajax({
        type: 'POST',
        url: href,
        headers: {"X-CSRFToken": csrf},
        context: click_this,
        success: function(data, textStatus, xhr) {
            if(xhr.status == 200) {
                // we delete a row in a table
                if(href.indexOf("rules") != -1) {
                    $(this).closest('tr').fadeOut(500, function() {
                        $(this).remove();
                    });
                } 
                // we delete the whole div around the table
                else {
                    // we need to readd the deleted group to the select
                    group_pk = parseInt($(this).closest('h4').attr('id'));
                    group_name = $(this).closest('h4').text();
                    
                    $(this).closest('div').fadeOut(500, function() {
                        $(this).remove();
                        $('#add_group')
                            .append($("<option></option>")
                            .attr('value', group_pk)
                            .text(group_name));
                    });
                }
            }
        }
    });
    return false;
}





/**                                                                         
 * Getter for user cookies                                                  
 * @param  {String} name Cookie name                                        
 * @return {String}      Cookie value                                       
 */                                                                         
                                                                            
function getCookie(name) {                                                  
  var cookieValue = null;                                                   
  if (document.cookie && document.cookie != '') {                           
    var cookies = document.cookie.split(';');                               
    for (var i = 0; i < cookies.length; i++) {                              
      var cookie = jQuery.trim(cookies[i]);                                 
      if (cookie.substring(0, name.length + 1) == (name + '=')) {           
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;                                                              
      }                                                                     
    }                                                                       
  }                                                                         
  return cookieValue;                                                       
} 
