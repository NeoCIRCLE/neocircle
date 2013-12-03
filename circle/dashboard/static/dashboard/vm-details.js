$(function() {
  if($('.timeline .activity:first i:first').hasClass('icon-spin'))
    checkNewActivity();

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
        addMessage("Eww, something is wrong", 'danger');
        if (xhr.status == 500) {
          // alert("uhuhuhuhuhuh");
        } else {
          // alert("unknown error");
        }
      }
    });
    return false;
  });

  /* rename */
  $("#vm-details-h1-name, .vm-details-rename-button").click(function() {
    $("#vm-details-h1-name").hide();
    $("#vm-details-rename").css('display', 'inline');
  });

  /* rename ajax */
  $('#vm-details-rename-submit').click(function() {
    var name = $('#vm-details-rename-name').val();
    $.ajax({
      method: 'POST',
      url: location.href,
      data: {'new_name': name},
      headers: {"X-CSRFToken": getCookie('csrftoken')},
      success: function(data, textStatus, xhr) {
        $("#vm-details-h1-name").html(data['new_name']).show();
        $('#vm-details-rename').hide();
        // addMessage(data['message'], "success");
      },
      error: function(xhr, textStatus, error) {
        addMessage("uhoh", "danger");
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

function checkNewActivity() {
  var latest = $('.activity:first').data('activity-id');
  var latest_sub = $('div[data-activity-id="' + latest + '"] .sub-timeline .sub-activity:first').data('activity-id');
  var instance = location.href.split('/'); instance = instance[instance.length - 2];

  $.ajax({
    type: 'POST',
    url: '/dashboard/vm/' + instance + '/activity/',
    headers: {"X-CSRFToken": getCookie('csrftoken')},
    data: {'latest': latest, 'latest_sub': latest_sub},
    success: function(data) {
      if(data['new_sub_activities'].length > 0) {
        d = data['new_sub_activities'];
        html = ""
        for(var i=0; i<d.length; i++) {
          html += '<div data-activity-id="' + d[i].id + '" class="sub-activity">' + d[i].name + ' - ';
          if(d[i].finished != null) {
            html += d[i].finished
          } else {
            html += '<i class="icon-refresh icon-spin" class="sub-activity-loading-icon"></i>';
          }
          html += '</div>';
        }
        $('div[data-activity-id="' + latest_sub + '"] .sub-activity .sub-activity-loading-icon').remove();
        $('div[data-activity-id="' + latest + '"] .sub-timeline').prepend(html);
      }

      if(data['is_parent_finished']) {
        var c = "icon-plus"
        $('div[data-activity-id="' + latest + '"] .icon-refresh.icon-spin:first').removeClass('icon-refresh').removeClass('icon-spin').addClass(c);
      }

      if(data['latest_sub_finished'] != null) {
        s = $('div[data-activity-id="' + latest_sub + '"]')
        $('.icon-refresh.icon-spin', s).remove();
        $(s).append(data['latest_sub_finished']);
      }

      if(data['is_parent_finished'])
        return;
      else
        setTimeout(checkNewActivity, 1000);
    },
    error: function() {

    }
  });
}


