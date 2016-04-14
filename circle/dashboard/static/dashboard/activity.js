$(function() {
  var in_progress = false;
  var activity_hash = 5;
  var show_all = false;
  var reload_vm_detail = false;

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

  /* operations */
  $('#ops, #vm-details-resources-disk, #vm-details-renew-op, #vm-details-pw-reset, #vm-details-add-interface, .operation-wrapper').on('click', '.operation', function(e) {
    var icon = $(this).children("i").addClass('fa-spinner fa-spin');

    $.ajax({
      type: 'GET',
      url: $(this).attr('href'),
      success: function(data) {
        icon.removeClass("fa-spinner fa-spin");
        $('body').append(data);
        $('#confirmation-modal').modal('show');
        $('#confirmation-modal').on('hidden.bs.modal', function() {
          $('#confirmation-modal').remove();
        });
        $('#vm-migrate-node-list li input:checked').closest('li').addClass('panel-primary');
      }
    });
    e.preventDefault();
  });

  /* if the operation fails show the modal again */
  $("body").on("click", "#confirmation-modal #op-form-send", function() {
    var url = $(this).closest("form").prop("action");

    $.ajax({
      url: url,
      headers: {"X-CSRFToken": getCookie('csrftoken')},
      type: 'POST',
      data: $(this).closest('form').serialize(),
      success: function(data, textStatus, xhr) {
        /* hide the modal we just submitted */
        $('#confirmation-modal').modal("hide");

        /* if it was successful trigger a click event on activity, this will
         *      - go to that tab
         *      - starts refreshing the activity
         */
        if(data.success) {
          $('a[href="#activity"]').trigger("click");
          if(data.with_reload) {
            // when the activity check stops the page will reload
            reload_vm_detail = true;
          }

          /* if there are messages display them */
          if(data.messages && data.messages.length > 0) {
            addMessage(data.messages.join("<br />"), data.success ? "success" : "danger");
          }
        }
        else {
          /* if the post was not successful wait for the modal to disappear
           * then append the new modal
           */
          $('#confirmation-modal').on('hidden.bs.modal', function() {
            $('body').append(data);
            $('#confirmation-modal').modal('show');
            $('#confirmation-modal').on('hidden.bs.modal', function() {
                $('#confirmation-modal').remove();
            });
          });
        }
      },
      error: function(xhr, textStatus, error) {
        $('#confirmation-modal').modal("hide");

        if (xhr.status == 500) {
          addMessage("500 Internal Server Error", "danger");
        } else {
          addMessage(xhr.status + " Unknown Error", "danger");
        }
      }
    });
    return false;
  });

  function decideActivityRefresh() {
    var check = false;
    /* if something is still spinning */
    if($('.timeline .activity i').hasClass('fa-spin'))
      check = true;

    return check;
  }

  function checkNewActivity(runs) {
    $.ajax({
      type: 'GET',
      url: $('a[href="#activity"]').attr('data-activity-url'),
      data: {'show_all': show_all},
      success: function(data) {
        var new_activity_hash = (data.activities + "").hashCode();
        if(new_activity_hash != activity_hash) {
          $("#activity-refresh").html(data.activities);
        }
        activity_hash = new_activity_hash;

        $("#ops").html(data.ops);
        $("#disk-ops").html(data.disk_ops);
        $("[title]").tooltip();

        /* changing the status text */
        var icon = $("#vm-details-state i");
        if(data.is_new_state) {
          if(!icon.hasClass("fa-spin"))
            icon.prop("class", "fa fa-spinner fa-spin");
        } else {
          icon.prop("class", "fa " + data.icon);
        }
        var vm_state = $("#vm-details-state");
        if (vm_state.length) {
          vm_state.data("status", data['status']); // jshint ignore:line
          $("#vm-details-state span").html(data.human_readable_status.toUpperCase());
        }
        if(data['status'] == "RUNNING") {  // jshint ignore:line
          if(data.connect_uri) {
              $("#dashboard-vm-details-connect-button").removeClass('disabled');
          }
          $("[data-target=#_console]").attr("data-toggle", "pill").attr("href", "#console").parent("li").removeClass("disabled");
          $("#getScreenshotButton").prop("disabled", false);
        } else {
          if(data.connect_uri) {
              $("#dashboard-vm-details-connect-button").addClass('disabled');
          }
          $("[data-target=#_console]").attr("data-toggle", "_pill").attr("href", "#").parent("li").addClass("disabled");
          $("#getScreenshotButton").prop("disabled", true);
        }

        if(data.status == "STOPPED" || data.status == "PENDING") {
          $(".change-resources-button").prop("disabled", false);
          $(".change-resources-help").hide();
        } else {
          $(".change-resources-button").prop("disabled", true);
          $(".change-resources-help").show();
        }

        if(runs > 0 && decideActivityRefresh()) {
          setTimeout(
            function() {checkNewActivity(runs + 1);},
            1000 + Math.exp(runs * 0.05)
          );
        } else {
          in_progress = false;
          if(windowHasFocus === false){
            sendNotification(generateMessageFromLastActivity());
          }
          if(reload_vm_detail) location.reload();
          if(runs > 1) addConnectText();
        }
        $('a[href="#activity"] i').removeClass('fa-spin');
      },
      error: function() {
        in_progress = false;
      }
    });
  }
});

// Notification init
$(function(){
  Notification.requestPermission();
});

// Detect window has focus
windowHasFocus = true;
$(window).blur(function(){
  windowHasFocus = false;
});
$(window).focus(function(){
  windowHasFocus = true;
});

function generateMessageFromLastActivity(){
  var ac = $('div.activity').first();
  if(ac.length === 0) return "";
  var error = $(ac[0]).children(".timeline-icon-failed").length;
  var sign = (error === 1) ? "❌ " : "✓ ";
  return sign + ac[0].innerText.split(",")[0];
}

function sendNotification(message) {
  if (Notification.permission === "granted") {
    var notification = new Notification(message);
  }
  else if (Notification.permission !== 'denied') {
    Notification.requestPermission(function (permission) {
      if (permission === "granted") {
        var notification = new Notification(message);
      }
    });
  }
}

function addConnectText() {
  var activities = $(".timeline .activity");
  if(activities.length > 1) {
    if(activities.eq(0).data("activity-code") == "vm.Instance.wake_up" ||
       activities.eq(0).data("activity-code") == "vm.Instance.agent") {
      $("#vm-detail-successfull-boot").slideDown(500);
    }
  }
}


String.prototype.hashCode = function() {
  var hash = 0, i, chr, len;
  if (this.length === 0) return hash;
  for (i = 0, len = this.length; i < len; i++) {
    chr   = this.charCodeAt(i);
    hash  = ((hash << 5) - hash) + chr;
    hash |= 0; // Convert to 32bit integer
  }
  return hash;
};

