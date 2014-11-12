var show_all = false;
var in_progress = false;
var activity_hash = 5;
var reload_vm_detail = false;

$(function() {
  /* do we need to check for new activities */
  if(decideActivityRefresh()) {
    if(!in_progress) {
      checkNewActivity(1);
      in_progress = true;
    }
  }

  $('a[href="#activity"]').click(function(){
    $('a[href="#activity"] i').addClass('fa-spin');
    if(!in_progress) {
      checkNewActivity(1);
      in_progress = true;
    }
  });

  $("#activity-refresh").on("click", "#show-all-activities", function() {
    $(this).find("i").addClass("fa-spinner fa-spin");
    show_all = !show_all;
    $('a[href="#activity"]').trigger("click");
    return false;
  });

  /* save resources */
  $('#vm-details-resources-save').click(function(e) {
    var error = false;
    $(".cpu-count-input, .ram-input").each(function() {
      if(!$(this)[0].checkValidity()) {
        error = true;
      }
    });
    if(error) return true;


    $('i.fa-floppy-o', this).removeClass("fa-floppy-o").addClass("fa-refresh fa-spin");
    var vm = $(this).data("vm");
    $.ajax({
      type: 'POST',
      url: "/dashboard/vm/" + vm + "/op/resources_change/", 
      data: $('#vm-details-resources-form').serialize(),
      success: function(data, textStatus, xhr) {
        if(data.success) {
          $('a[href="#activity"]').trigger("click");
        } else {
          addMessage(data.messages.join("<br />"), "danger");
        }
        $("#vm-details-resources-save i").removeClass('fa-refresh fa-spin').addClass("fa-floppy-o");
      },
      error: function(xhr, textStatus, error) {
        $("#vm-details-resources-save i").removeClass('fa-refresh fa-spin').addClass("fa-floppy-o");
        if (xhr.status == 500) {
          addMessage("500 Internal Server Error", "danger");
        } else {
          addMessage(xhr.status + " Unknown Error", "danger");
        }  
      }
    });
    e.preventDefault();
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
    var span = $(this);
    
    span.tooltip("destroy")
    if(eye.hasClass("fa-eye")) {
      eye.removeClass("fa-eye").addClass("fa-eye-slash");
      input.prop("type", "text");
      input.select();
      span.prop("title", gettext("Hide password"));
    } else {
      eye.removeClass("fa-eye-slash").addClass("fa-eye");
      input.prop("type", "password");
      span.prop("title", gettext("Show password"));
    }
    span.tooltip();
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
        location.reload();
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
    $("#vm-details-rename-name").select();
    return false;
  });

  /* rename in home tab */
  $(".vm-details-home-edit-name-click").click(function(e) {
    $(".vm-details-home-edit-name-click").hide();
    $("#vm-details-home-rename").show();
    $("input", $("#vm-details-home-rename")).select();
    e.preventDefault();
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
  $(".vm-details-home-edit-description-click").click(function(e) {
    $(".vm-details-home-edit-description-click").hide();
    $("#vm-details-home-description").show();
    var ta = $("#vm-details-home-description textarea");
    var tmp = ta.val();
    ta.val("");
    ta.focus();
    ta.val(tmp)
    e.preventDefault();
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
    $("i", this).addClass("fa-spinner fa-spin");
    $(this).prop("disabled", true);
    ct.slideDown();
    var img = $("img", ct).prop("src", '/dashboard/vm/' + vm + '/screenshot/');
  });

  // if the image is loaded remove the spinning stuff
  // note: this should not work if the image is cached, but it's not
  // see: http://stackoverflow.com/a/3877079/1112653
  $("#vm-console-screenshot img").load(function(e) {
    $("#getScreenshotButton").prop("disabled", false)
    .find("i").removeClass("fa-spinner fa-spin");

  });
    
  
  // screenshot close
  $("#vm-console-screenshot button").click(function() {
    $(this).parent("div").slideUp();
  });

  // select connection string
  $(".vm-details-connection-string-copy").click(function() {
    $(this).parent("div").find("input").select();
  });

  $("a.operation-password_reset").click(function() {
    if(Boolean($(this).data("disabled"))) return false;
  });

  $("#dashboard-tutorial-toggle").click(function() {
    var box = $("#alert-new-template");
    var list = box.find("ol")
    list.stop().slideToggle(function() {
      var url = box.find("form").prop("action");
      var hidden = list.css("display") === "none";
      box.find("button i").prop("class", "fa fa-caret-" + (hidden ? "down" : "up"));
      $.ajax({
        type: 'POST',
        url: url,
        data: {'hidden': hidden},
        headers: {"X-CSRFToken": getCookie('csrftoken')},
        success: function(re, textStatus, xhr) {}
      });
    }); 
    return false;
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
  if($('.timeline .activity i').hasClass('fa-spin'))
    check = true;

  return check;
}

function checkNewActivity(runs) {
  var instance = location.href.split('/'); instance = instance[instance.length - 2];

  $.ajax({
    type: 'GET',
    url: '/dashboard/vm/' + instance + '/activity/',
    data: {'show_all': show_all},
    success: function(data) {
      var new_activity_hash = (data['activities'] + "").hashCode();
      if(new_activity_hash != activity_hash) {
        $("#activity-refresh").html(data['activities']);
      }
      activity_hash = new_activity_hash;

      $("#ops").html(data['ops']);
      $("#disk-ops").html(data['disk_ops']);
      $("[title]").tooltip();

      /* changing the status text */
      var icon = $("#vm-details-state i");
      if(data['is_new_state']) {
        if(!icon.hasClass("fa-spin"))
          icon.prop("class", "fa fa-spinner fa-spin");
      } else {
        icon.prop("class", "fa " + data['icon']);
      }
      $("#vm-details-state").data("status", data['status']);
      $("#vm-details-state span").html(data['human_readable_status'].toUpperCase());
      if(data['status'] == "RUNNING") {
        if(data['connect_uri']) {
            $("#dashboard-vm-details-connect-button").removeClass('disabled');
        }
        $("[data-target=#_console]").attr("data-toggle", "pill").attr("href", "#console").parent("li").removeClass("disabled");
      } else {
        if(data['connect_uri']) {
            $("#dashboard-vm-details-connect-button").addClass('disabled');
        }
        $("[data-target=#_console]").attr("data-toggle", "_pill").attr("href", "#").parent("li").addClass("disabled");
      }

      if(data['status'] == "STOPPED" || data['status'] == "PENDING") {
        $(".change-resources-button").prop("disabled", false);
        $(".change-resources-help").hide();
      } else {
        $(".change-resources-button").prop("disabled", true);
        $(".change-resources-help").show();
      }

      if(runs > 0 && decideActivityRefresh()) {
        setTimeout(
          function() {checkNewActivity(runs + 1)}, 
          1000 + Math.exp(runs * 0.05)
        );
      } else {
        in_progress = false;
        if(reload_vm_detail) location.reload();
      }
      $('a[href="#activity"] i').removeClass('fa-spin');
    },
    error: function() {
      in_progress = false;
    }
  });
}

String.prototype.hashCode = function() {
  var hash = 0, i, chr, len;
  if (this.length == 0) return hash;
  for (i = 0, len = this.length; i < len; i++) {
    chr   = this.charCodeAt(i);
    hash  = ((hash << 5) - hash) + chr;
    hash |= 0; // Convert to 32bit integer
  }
  return hash;
};
