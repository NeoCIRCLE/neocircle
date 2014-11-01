var in_progress = false;
var activity_hash = 5;

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

  $('a.operation.btn').click(function(e) {
    $.ajax({
      type: 'GET',
      url: $(this).attr('href'),
      success: function(data) {
        $('body').append(data);
        $('#confirmation-modal').modal('show');
        $('#confirmation-modal').on('hidden.bs.modal', function() {
          $('#confirmation-modal').remove();
        });
      }
    });
    return false;
  });

  /* rename */
  $("#node-details-h1-name, .node-details-rename-button").click(function() {
    $("#node-details-h1-name").hide();
    $("#node-details-rename").css('display', 'inline');
    $("#node-details-rename-name").focus();
  });

  /* rename ajax */
  $('#node-details-rename-submit').click(function() {
    var name = $('#node-details-rename-name').val();
    $.ajax({
      method: 'POST',
      url: location.href,
      data: {'new_name': name},
      headers: {"X-CSRFToken": getCookie('csrftoken')},
      success: function(data, textStatus, xhr) {
        $("#node-details-h1-name").text(data['new_name']).show();
        $('#node-details-rename').hide();
        // addMessage(data.message, "success");
      },
      error: function(xhr, textStatus, error) {
        addMessage("Error during renaming!", "danger");
      }
    });
    return false;
  });

  $(".node-details-help-button").click(function() {
    $(".node-details-help").stop().slideToggle();
  });

  // remove trait
  $('.node-details-remove-trait').click(function() {
    var to_remove =  $(this).data("trait-pk");
    var clicked = $(this);
    $.ajax({
      type: 'POST',
      url: location.href,
      headers: {"X-CSRFToken": getCookie('csrftoken')},
      data: {'to_remove': to_remove},
      success: function(re) {
        if(re.message.toLowerCase() == "success") {
          $(clicked).closest(".label").fadeOut(500, function() {
            $(this).remove();
          });
        }
      },
      error: function() {
        addMessage(re.message, 'danger');
      }

    });
    return false;
  });

});

function decideActivityRefresh() {
  var check = false;
  /* if something is still spinning */
  if($('.timeline .activity i').hasClass('fa-spin'))
    check = true;

  return check;
}

function checkNewActivity(runs) {
  var node = location.href.split('/'); node = node[node.length - 2];

  $.ajax({
    type: 'GET',
    url: '/dashboard/node/' + node + '/activity/',
    success: function(data) {
      var new_activity_hash = (data['activities'] + "").hashCode();
      if(new_activity_hash != activity_hash) {
        $("#activity-refresh").html(data['activities']);
      }
      activity_hash = new_activity_hash;

      $("[title]").tooltip();

      if(runs > 0 && decideActivityRefresh()) {
        setTimeout(
          function() {checkNewActivity(runs + 1)},
          1000 + Math.exp(runs * 0.05)
        );
      } else {
        in_progress = false;
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
