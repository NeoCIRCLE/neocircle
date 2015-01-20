// for AJAX calls

/**
 * Getter for user cookies
 * @param  {String} name Cookie name
 * @return {String}      Cookie value
 */

function getCookie(name) {
  var cookieValue = null;
  if (document.cookie && document.cookie !== '') {
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

function doBlink(id, count) {
    if (count > 0) {
        $(id).parent().delay(200).queue(function() {
            $(this).delay(200).queue(function() {
                $(this).removeClass("has-warning").dequeue();
                doBlink(id, count-1);});
            $(this).addClass("has-warning").dequeue();
        });
    }
}

$(function() {
  $("[title]").tooltip();

$("#ipv6-magic").click(function() {
    $.ajax({url: window.location,
            data: {ipv4: $("[name=ipv4]").val(),
                   vlan: $("[name=vlan]").val()},
            success: function(data) {
                       $("[name=ipv6]").val(data.ipv6);
            }});
});
$("#ipv4-magic").click(function() {
    $.ajax({url: window.location,
            data: {vlan: $("[name=vlan]").val()},
            success: function(data) {
                $("[name=ipv4]").val(data.ipv4);
                if ($("[name=ipv6]").val() != data.ipv6) {
                    doBlink("[name=ipv6]", 3);
                }
                $("[name=ipv6]").val(data.ipv6);
            }});
});
$("#ipv6-tpl-magic").click(function() {
    $.ajax({url: window.location,
            data: {network4: $("[name=network4]").val(),
                   network6: $("[name=network6]").val()},
            success: function(data) {
                       $("[name=ipv6_template]").val(data.ipv6_template);
                       if ($("[name=host_ipv6_prefixlen]").val() != data.host_ipv6_prefixlen) {
                           doBlink("[name=host_ipv6_prefixlen]", 3);
                       }
                       $("[name=host_ipv6_prefixlen]").val(data.host_ipv6_prefixlen);
            }});
});
});
