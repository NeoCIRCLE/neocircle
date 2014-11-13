// for AJAX calls

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


function getURLParameter(name) {
    return decodeURI(
        (RegExp(name + '=' + '(.+?)(&|$)').exec(location.search)||[,null])[1]
    );
}

$(function() {
  $("[title]").tooltip();

$("#ipv6-magic").click(function() {
    $.ajax({url: window.location,
            data: {ipv4: $("[name=ipv4]").val(),
                   vlan: $("[name=vlan]").val()},
            success: function(data) {
                       $("[name=ipv6]").val(data["ipv6"]);
            }});
});
$("#ipv4-magic").click(function() {
    $.ajax({url: window.location,
            data: {vlan: $("[name=vlan]").val()},
            success: function(data) {
                       $("[name=ipv4]").val(data["ipv4"]);
                       if (!$("[name=ipv6]").val()) {
                         $("[name=ipv6]").val(data["ipv6"]);
                       }
            }});
});
$("#ipv6-tpl-magic").click(function() {
    $.ajax({url: window.location,
            data: {network4: $("[name=network4]").val(),
                   network6: $("[name=network6]").val()},
            success: function(data) {
                       $("[name=ipv6_template]").val(data["ipv6_template"]);
            }});
});
});
