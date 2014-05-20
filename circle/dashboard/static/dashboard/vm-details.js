$(function() {
  /* do we need to check for new activities */
  if(decideActivityRefresh()) {
    checkNewActivity(false, 1);
  }
  $('a[href="#activity"]').click(function(){
    $('a[href="#activity"] i').addClass('icon-spin');
    checkNewActivity(false,0);
  });

  /* save resources */
  $('#vm-details-resources-save').click(function() {
    $('i.icon-save', this).removeClass("icon-save").addClass("icon-refresh icon-spin");
    $.ajax({
      type: 'POST',
      url: location.href,
      data: $('#vm-details-resources-form').serialize(),
      success: function(data, textStatus, xhr) {
        addMessage(data['message'], 'success');
        $("#vm-details-resources-save i").removeClass('icon-refresh icon-spin').addClass("icon-save");
      },
      error: function(xhr, textStatus, error) {
        $("#vm-details-resources-save i").removeClass('icon-refresh icon-spin').addClass("icon-save");
        if (xhr.status == 500) {
          addMessage("500 Internal Server Error", "danger");
        } else {
          addMessage(xhr.status + " Unknown Error", "danger");
        }  
      }
    });
    return false;
  });

  /* remove tag */
  $('.vm-details-remove-tag').click(function() {
    var to_remove =  $.trim($(this).parent('div').text());
    var clicked = $(this);
    $.ajax({
      type: 'POST',
      url: location.href,
      headers: {"X-CSRFToken": getCookie('csrftoken')}, 
      data: {'to_remove': to_remove},
      success: function(re) {
        if(re['message'].toLowerCase() == "success") {
          $(clicked).closest(".label").fadeOut(500, function() {
            $(this).remove();
          });
        }
      },
      error: function() {
        addMessage(re['message'], 'danger');
      }

    });
    return false;
  });

  /* remove port */
  $('.vm-details-remove-port').click(function() {
    addModalConfirmation(removePort, 
      {
        'url': $(this).prop("href"),
        'data': [],
        'rule': $(this).data("rule")
      });
    return false;
  });

  /* for js fallback */
  $("#vm-details-pw-show").parent("div").children("input").prop("type", "password");
  
  /* show password */
  $("#vm-details-pw-show").click(function() {
    var input = $(this).parent("div").children("input");
    var eye = $(this).children("#vm-details-pw-eye");
    
    eye.tooltip("destroy")
    if(eye.hasClass("icon-eye-open")) {
      eye.removeClass("icon-eye-open").addClass("icon-eye-close");
      input.prop("type", "text");
      input.focus();
      eye.prop("title", "Hide password");
    } else {
      eye.removeClass("icon-eye-close").addClass("icon-eye-open");
      input.prop("type", "password");
      eye.prop("title", "Show password");
    }
    eye.tooltip();
  });

  /* change password confirmation */
  $("#vm-details-pw-change").click(function() {
    $("#vm-details-pw-confirm").fadeIn();
    return false;
  });

  /* change password */
  $(".vm-details-pw-confirm-choice").click(function() {
    choice = $(this).data("choice");
    if(choice) {
      pk = $(this).data("vm");
      $.ajax({
        type: 'POST',
        url: "/dashboard/vm/" + pk + "/",
        data: {'change_password': 'true'},
        headers: {"X-CSRFToken": getCookie('csrftoken')},
        success: function(re, textStatus, xhr) {
          location.reload();
        },
        error: function(xhr, textStatus, error) {
          if (xhr.status == 500) {
            addMessage("Internal Server Error", "danger");
          } else {
            addMessage(xhr.status + " Unknown Error", "danger");
          }
        }
      });
    } else {
      $("#vm-details-pw-confirm").fadeOut(); 
    }
    return false;
  });

  /* add network button */
  $("#vm-details-network-add").click(function() {
    $("#vm-details-network-add-form").toggle();
    return false;
  });

  /* add disk button */
  $("#vm-details-disk-add").click(function() {
    $("#vm-details-disk-add-for-form").html($("#vm-details-disk-add-form").html());
    return false;
  });

  /* show help */
  $(".vm-details-help-button").click(function() {
    $(".vm-details-help").stop().slideToggle();
  });

  /* for interface remove buttons */
  $('.interface-remove').click(function() {
    var interface_pk = $(this).data('interface-pk');
    addModalConfirmation(removeInterface, 
      { 'url': '/dashboard/interface/' + interface_pk + '/delete/',
        'data': [],
        'pk': interface_pk,
	'type': "interface",
      });
    return false;
  });

  /* removing interface post */
  function removeInterface(data) {
    $.ajax({
      type: 'POST',
      url: data['url'],
      headers: {"X-CSRFToken": getCookie('csrftoken')}, 
      success: function(re, textStatus, xhr) { 
        /* remove the html element */
        $('a[data-interface-pk="' + data.pk + '"]').closest("div").fadeOut();
        
        /* add the removed element to the list */
        network_select = $('select[name="new_network_vlan"]');
        name_html = (re.removed_network.managed ? "&#xf0ac;": "&#xf0c1;") + " " + re.removed_network.vlan;
        option_html = '<option value="' + re.removed_network.vlan_pk + '">' + name_html + '</option>';
        // if it's -1 then it's a dummy placeholder so we can use .html
        if($("option", network_select)[0].value === "-1") {
          network_select.html(option_html);
          network_select.next("div").children("button").prop("disabled", false); 
        } else {
          network_select.append(option_html);
        }
      },
      error: function(xhr, textStatus, error) {
        addMessage('Uh oh :(', 'danger')
      }
    });
  }

  /* rename */
  $("#vm-details-h1-name, .vm-details-rename-button").click(function() {
    $("#vm-details-h1-name").hide();
    $("#vm-details-rename").css('display', 'inline');
    $("#vm-details-rename-name").focus();
    return false;
  });

  /* rename in home tab */
  $(".vm-details-home-edit-name-click").click(function() {
    $(".vm-details-home-edit-name-click").hide();
    $("#vm-details-home-rename").show();
    $("input", $("#vm-details-home-rename")).focus();
    return false;
  });

  /* rename ajax */
  $('.vm-details-rename-submit').click(function() {
    var name = $(this).parent("span").prev("input").val();
    $.ajax({
      method: 'POST',
      url: location.href,
      data: {'new_name': name},
      headers: {"X-CSRFToken": getCookie('csrftoken')},
      success: function(data, textStatus, xhr) {
        $(".vm-details-home-edit-name").text(data['new_name']).show();
        $(".vm-details-home-edit-name").parent("div").show();
        $(".vm-details-home-edit-name-click").show();
        $(".vm-details-home-rename-form-div").hide();
        // update the inputs too
        $(".vm-details-rename-submit").parent("span").prev("input").val(data['new_name']);  
      },
      error: function(xhr, textStatus, error) {
        addMessage("Error during renaming!", "danger");
      }
    });
    return false;
  });
  
  /* update description click */
  $(".vm-details-home-edit-description-click").click(function() {
    $(".vm-details-home-edit-description-click").hide();
    $("#vm-details-home-description").show();
    var ta = $("#vm-details-home-description textarea");
    var tmp = ta.val();
    ta.val("");
    ta.focus();
    ta.val(tmp)
    return false;
  });
  
  /* description update ajax */
  $('.vm-details-description-submit').click(function() {
    var description = $(this).prev("textarea").val();
    $.ajax({
      method: 'POST',
      url: location.href,
      data: {'new_description': description},
      headers: {"X-CSRFToken": getCookie('csrftoken')},
      success: function(data, textStatus, xhr) {
        var new_desc = data['new_description'];
        /* we can't simply use $.text, because we need new lines */ 
        var tagsToReplace = {
          '&': "&amp;",
          '<': "&lt;",
          '>': "&gt;",
        };
        
        new_desc = new_desc.replace(/[&<>]/g, function(tag) {
          return tagsToReplace[tag] || tag;
        });

        $(".vm-details-home-edit-description")
          .html(new_desc.replace(/\n/g, "<br />"));
        $(".vm-details-home-edit-description-click").show();
        $("#vm-details-home-description").hide();
        // update the textareia
        $("vm-details-home-description textarea").text(data['new_description']);  
      },
      error: function(xhr, textStatus, error) {
        addMessage("Error during renaming!", "danger");
      }
    });
    return false;
  });

  // screenshot
  $("#getScreenshotButton").click(function() {
    var vm = $(this).data("vm-pk");
    var ct = $("#vm-console-screenshot");
    ct.slideDown();
    var img = $("img", ct).prop("src", '/dashboard/vm/' + vm + '/screenshot/');
  });
  
  // screenshot close
  $("#vm-console-screenshot button").click(function() {
    $(this).parent("div").slideUp();
  });

});


function removePort(data) {
  $.ajax({
    type: 'POST',
    url: data['url'],
    headers: {"X-CSRFToken": getCookie('csrftoken')},
    success: function(re, textStatus, xhr) {
      $("a[data-rule=" + data['rule'] + "]").each(function() {
        $(this).closest("tr").fadeOut(500, function() {
          $(this).remove();
        });
      });
      addMessage(re['message'], "success");
    },
    error: function(xhr, textStatus, error) {

    }
  });
}

function decideActivityRefresh() {
  var check = false;
  /* if something is still spinning */
  if($('.timeline .activity:first i:first').hasClass('icon-spin'))
    check = true;
  /* if there is only one activity */
  if($('#activity-timeline div[class="activity"]').length < 2)
    check = true;

  return check;
}

function checkNewActivity(only_status, runs) {
  // set default only_status to false
  only_status = typeof only_status !== 'undefined' ? only_status : false;
  var instance = location.href.split('/'); instance = instance[instance.length - 2];

  $.ajax({
    type: 'GET',
    url: '/dashboard/vm/' + instance + '/activity/',
    data: {'only_status': only_status},
    success: function(data) {
      if(!only_status) {
        $("#activity-timeline").html(data['activities']);
        $("#ops").html(data['ops']);
        $("[title]").tooltip();
      }

      $("#vm-details-state i").prop("class", data['icon']);
      $("#vm-details-state span").html(data['human_readable_status'].toUpperCase());
      if(data['status'] == "RUNNING") {
        $("[data-target=#_console]").attr("data-toggle", "pill").attr("href", "#console").parent("li").removeClass("disabled");
      } else {
        $("[data-target=#_console]").attr("data-toggle", "_pill").attr("href", "#").parent("li").addClass("disabled");
      }

      if(runs > 0 && decideActivityRefresh()) {
        setTimeout(
          function() {checkNewActivity(only_status, runs + 1)}, 
          1000 + Math.exp(runs * 0.05)
        );
      }
      $('a[href="#activity"] i').removeClass('icon-spin');
    },
    error: function() {

    }
  });
}
