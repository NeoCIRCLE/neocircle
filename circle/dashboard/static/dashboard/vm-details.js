
$(function() {
  if($('.timeline .activity:first i:first').hasClass('icon-spin'))
    checkNewActivity();
});

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


