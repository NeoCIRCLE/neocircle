$(function () {
  $('.vm-create').click(function(e) {
    var template = $(this).data("template");
    $.ajax({
      type: 'GET',
      url: '/dashboard/vm/create/' + (typeof template === "undefined" ? '' : '?template=' + template),
      success: function(data) {
        $('body').append(data);
        vmCreateLoaded();
        addSliderMiscs();
        $('#create-modal').modal('show');
        $('#create-modal').on('hidden.bs.modal', function() {
          $('#create-modal').remove();
        });
      }
    });
    return false;
  });

  $('.node-create').click(function(e) {
    $.ajax({
      type: 'GET',
      url: '/dashboard/node/create/',
      success: function(data) {
        $('body').append(data);
        nodeCreateLoaded();
        addSliderMiscs();
        $('#create-modal').modal('show');
        $('#create-modal').on('hidden.bs.modal', function() {
          $('#create-modal').remove();
        });
      }
    });
    return false;
  });

  $('.group-create').click(function(e) {
    $.ajax({
      type: 'GET',
      url: '/dashboard/group/create/',
      success: function(data) {
        $('body').append(data);
        addSliderMiscs();
        $('#create-modal').modal('show');
        $('#create-modal').on('hidden.bs.modal', function() {
          $('#create-modal').remove();
        });
      }
    });
    return false;
  });

  $('.template-choose').click(function(e) {
    $.ajax({
      type: 'GET',
      url: '/dashboard/template/choose/',
      success: function(data) {
        $('body').append(data);
        $('#create-modal').modal('show');
        $('#create-modal').on('hidden.bs.modal', function() {
          $('#create-modal').remove();
        });
        // check if user selected anything
        $("#template-choose-next-button").click(function() {
          var radio = $('input[type="radio"]:checked', "#template-choose-form").val();
          if(!radio) {
            $("#template-choose-alert").addClass("alert-warning")
            .text(gettext("Select an option to proceed!"));
            return false;
          }
          return true;
        });
      }
    });
    return false;
  });

  $('[href=#index-graph-view]').click(function (e) {
    var box = $(this).data('index-box');
    $("#" + box + "-list-view").hide();
    $("#" + box + "-graph-view").show();
    $(this).next('a').removeClass('disabled');
    $(this).addClass('disabled');
    e.stopImmediatePropagation();
    return false;
  });
  $('[href=#index-list-view]').click(function (e) {
    var box = $(this).data('index-box');
    $('#' + box + '-graph-view').hide();
    $('#' + box + '-list-view').show();
    $(this).addClass('disabled');
    $(this).prev("a").removeClass('disabled');
    e.stopImmediatePropagation();
    return false;
  });
  $('[title]:not(.title-favourite)').tooltip();
  $('.title-favourite').tooltip({'placement': 'right'});
  $(':input[title]').tooltip({trigger: 'focus', placement: 'auto right'});
  $(".knob").knob();

  $('[data-toggle="pill"]').click(function() {
    window.location.hash = $(this).attr('href');
  });

  if (window.location.hash) {
    if(window.location.hash.substring(1,4) == "ipv")
      $("a[href=#network]").tab('show');
    if(window.location.hash == "activity")
      checkNewActivity(false, 1);
    $("a[href=" + window.location.hash +"]").tab('show');
  }


  /* no js compatibility */
  noJS();
  $('.no-js-hidden').show();
  $('.js-hidden').hide();

  /* favourite star */
  $("#dashboard-vm-list").on('click', '.dashboard-vm-favourite', function(e) {
    var star = $(this).children("i");
    var pk = $(this).data("vm");
    if(star.hasClass("fa-star-o")) {
      star.removeClass("fa-star-o").addClass("fa-star");
      star.prop("title", "Unfavourite");
    } else {
      star.removeClass("fa-star").addClass("fa-star-o");
      star.prop("title", "Mark as favourite");
    }
    $.ajax({
      url: "/dashboard/favourite/",
      type: "POST",
      data: {'vm': pk},
      headers: {"X-CSRFToken": getCookie('csrftoken')},
      success: function(data, textStatus, xhr) {
        // success
      },
      error: function(xhr, textStatus, error) {
        console.log("oh babám");
      }
    });
    $(star).tooltip('destroy').tooltip({'placement': 'right'});
    my_vms = [];
    return false;
  });

  /* scroll to top if there is a message */
  if($(".messagelist").children(".alert").length > 0)
    $('body').animate({scrollTop: 0});

  addSliderMiscs();

  /* for VM removes buttons */
  $('.vm-delete').click(function() {
    var vm_pk = $(this).data('vm-pk');
    var dir = window.location.pathname.indexOf('list') == -1;
    addModalConfirmation(deleteObject,
      { 'url': '/dashboard/vm/delete/' + vm_pk + '/',
        'data': [],
        'pk': vm_pk,
        'type': "vm",
        'redirect': dir});
    return false;
  });

  /* for disk remove buttons */
  $('.disk-remove').click(function() {
    var disk_pk = $(this).data('disk-pk');
    addModalConfirmation(deleteObject,
      { 'url': '/dashboard/disk/' + disk_pk + '/remove/',
        'data': [],
        'pk': disk_pk,
        'type': "disk",
      });
    return false;
  });

  /* for Node removes buttons */
  $('.node-delete').click(function() {
    var node_pk = $(this).data('node-pk');
    var dir = window.location.pathname.indexOf('list') == -1;
    addModalConfirmation(deleteObject,
      { 'url': '/dashboard/node/delete/' + node_pk + '/',
        'data': [],
        'pk': node_pk,
        'type': "node",
        'redirect': dir});

    return false;
  });

  /* for Node flush buttons */
  $('.node-flush').click(function() {
    var node_pk = $(this).data('node-pk');
    var postto = $(this).attr('href');
    var dir = window.location.pathname.indexOf('list') == -1;
    addModalConfirmation(function(){},
      { 'url': postto,
        'data': [],
        'pk': node_pk,
        'type': "node",
        'redirect': dir});

    return false;
  });

  /* for Group removes buttons */
  $('.group-delete').click(function() {
    var group_pk = $(this).data('group-pk');
    var dir = window.location.pathname.indexOf('list') == -1;
    addModalConfirmation(deleteObject,
      { 'url': '/dashboard/group/delete/' + group_pk + '/',
        'data': [],
        'type': "group",
        'pk': group_pk,
        'redirect': dir});

    return false;
  });

 /* search for vms */
  var my_vms = [];
  $("#dashboard-vm-search-input").keyup(function(e) {
    // if my_vms is empty get a list of our vms
    if(my_vms.length < 1) {
      $.ajaxSetup( { "async": false } );
      $.get("/dashboard/vm/list/", function(result) {
        for(var i in result) {
          my_vms.push({
            'pk': result[i].pk,
            'name': result[i].name.toLowerCase(),
            'state': result[i].state,
            'fav': result[i].fav,
            'host': result[i].host,
            'icon': result[i].icon,
            'status': result[i].status,
          });
        }
      });
      $.ajaxSetup( { "async": true } );
    }

    input = $("#dashboard-vm-search-input").val().toLowerCase();
    var search_result = [];
    var html = '';
    for(var i in my_vms) {
      if(my_vms[i].name.indexOf(input) != -1) {
        search_result.push(my_vms[i]);
      }
    }
    search_result.sort(compareVmByFav);
    for(i=0; i<5 && i<search_result.length; i++)
      html += generateVmHTML(search_result[i].pk, search_result[i].name,
                             search_result[i].host, search_result[i].icon,
                             search_result[i].status, search_result[i].fav,
                             (search_result.length < 5));
    if(search_result.length === 0)
      html += '<div class="list-group-item list-group-item-last">' + gettext("No result") + '</div>';
    $("#dashboard-vm-list").html(html);
    $('.title-favourite').tooltip({'placement': 'right'});
  });

  $("#dashboard-vm-search-form").submit(function() {
    var vm_list_items = $("#dashboard-vm-list .list-group-item");
    if(vm_list_items.length == 1 && vm_list_items.first().prop("href")) {
      window.location.href = vm_list_items.first().prop("href");
      return false;
    }
    return true;
  });

  /* search for nodes */
  var my_nodes = [];
  $("#dashboard-node-search-input").keyup(function(e) {
    // if my_nodes is empty get a list of our nodes
    if(my_nodes.length < 1) {
      $.ajaxSetup( { "async": false } );
      $.get("/dashboard/node/list/", function(result) {
        for(var i in result) {
          my_nodes.push({
            'name': result[i].name.toLowerCase(),
            'icon': result[i].icon,
            'status': result[i].status,
            'label': result[i].label,
            'url': result[i].url,
          });
        }
      });
      $.ajaxSetup( { "async": true } );
    }

    input = $("#dashboard-node-search-input").val().toLowerCase();
    var search_result = [];
    var html = '';
    for(var i in my_nodes) {
      if(my_nodes[i].name.indexOf(input) != -1) {
        search_result.push(my_nodes[i]);
      }
    }
    for(i=0; i<5 && i<search_result.length; i++)
      html += generateNodeHTML(search_result[i].name,
                             search_result[i].icon, search_result[i].status,
                             search_result[i].url,
                             (search_result.length < 5));
    if(search_result.length === 0)
      html += '<div class="list-group-item list-group-item-last">' + gettext("No result") + '</div>';
    $("#dashboard-node-list").html(html);

    html = '';

    for(i=0; i<5 && i<search_result.length; i++)
      html += generateNodeTagHTML(search_result[i].name,
                             search_result[i].icon, search_result[i].status,
                             search_result[i].label, search_result[i].url);
    if(search_result.length === 0)
      html += '<div class="list-group-item list-group-item-last">' + gettext("No result") + '</div>';
    $("#dashboard-node-taglist").html(html);

    // if there is only one result and ENTER is pressed redirect
    if(e.keyCode == 13 && search_result.length == 1) {
      window.location.href = search_result[0].url;
    }
    if(e.keyCode == 13 && search_result.length > 1 && input.length > 0) {
      window.location.href = "/dashboard/node/list/?s=" + input;
    }
  });

  /* search for groups */
  var my_groups = [];
  $("#dashboard-group-search-input").keyup(function(e) {
    // if my_groups is empty get a list of our groups
      if(my_groups.length < 1) {
      $.ajaxSetup( { "async": false } );
      $.get("/dashboard/group/list/", function(result) {
        for(var i in result) {
          my_groups.push({
            'url': result[i].url,
            'name': result[i].name.toLowerCase(),
          });
        }
      });
      $.ajaxSetup( { "async": true } );
    }

    input = $("#dashboard-group-search-input").val().toLowerCase();
    var search_result = [];
    var html = '';
    for(var i in my_groups) {
      if(my_groups[i].name.indexOf(input) != -1) {
        search_result.push(my_groups[i]);
      }
    }
    for(i=0; i<5 && i<search_result.length; i++)
      html += generateGroupHTML(search_result[i].url, search_result[i].name, search_result.length < 5);
    if(search_result.length === 0)
      html += '<div class="list-group-item list-group-item-last">No result</div>';
    $("#dashboard-group-list").html(html);

    // if there is only one result and ENTER is pressed redirect
    if(e.keyCode == 13 && search_result.length == 1) {
      window.location.href = search_result[0].url;
    }
    if(e.keyCode == 13 && search_result.length > 1 && input.length > 0) {
      window.location.href = "/dashboard/group/list/?s=" + input;
    }
  });

  /* notification message toggle */
  $(document).on('click', ".notification-message-subject", function() {
    $(".notification-message-text", $(this).parent()).slideToggle();
    return false;
  });

  /* don't close notifications window on missclick */
  $(document).on("click", ".notification-messages", function(e) {
    if($(e.target).closest("a").length)
      return true;
    else
      return false;
  });

  $("#notification-button a").click(function() {
    $('.notification-messages').load("/dashboard/notifications/");
    $('#notification-button a span[class*="badge-pulse"]').remove();
  });
});

function generateVmHTML(pk, name, host, icon, _status, fav, is_last) {
  return '<a href="/dashboard/vm/' + pk + '/" class="list-group-item' +
         (is_last ? ' list-group-item-last' : '') + '">' +
        '<span class="index-vm-list-name">' +
          '<i class="fa ' + icon + '" title="' + _status + '"></i> ' + name +
        '</span>' +
        '<small class="text-muted"> ' + host + '</small>' +
        '<div class="pull-right dashboard-vm-favourite" data-vm="' + pk + '">' +
          (fav ? '<i class="fa fa-star text-primary title-favourite" title="Unfavourite"></i>' :
          '<i class="fa fa-star-o text-primary title-favourite" title="Mark as favorite"></i>' ) +
        '</div>' +
      '<div style="clear: both;"></div>' +
      '</a>';
}

function generateGroupHTML(url, name, is_last) {
  return '<a href="' + url + '" class="list-group-item real-link' + (is_last ? " list-group-item-last" : "") +'">'+
         '<i class="fa fa-users"></i> '+ name +
         '</a>';
}

function generateNodeHTML(name, icon, _status, url, is_last) {
  return '<a href="' + url + '" class="list-group-item real-link' + (is_last ? ' list-group-item-last' : '') + '">' +
        '<span class="index-node-list-name">' +
        '<i class="fa ' + icon + '" title="' + _status + '"></i> ' + name +
        '</span>' +
        '<div style="clear: both;"></div>' +
        '</a>';
}

function generateNodeTagHTML(name, icon, _status, label , url) {
  return '<a href="' + url + '" class="label ' + label + '" >' +
        '<i class="' + icon + '" title="' + _status + '"></i> ' + name +
        '</a> ';
}

/* copare vm-s by fav, pk order */
function compareVmByFav(a, b) {
  if(a.fav && b.fav) {
    return a.pk < b.pk ? -1 : 1;
  }
  else if(a.fav && !b.fav) {
    return -1;
  }
  else if(!a.fav && b.fav) {
    return 1;
  }
  else
    return a.pk < b.pk ? -1 : 1;
}

$(document).on('shown.bs.tab', 'a[href="#resources"]', function (e) {
  $(".cpu-priority-input").trigger("change");
  $(".cpu-count-input, .ram-input").trigger("input");
});

function addSliderMiscs() {
  // set max values based on inputs
  var cpu_count_range = "0, " + $(".cpu-count-input").prop("max");
  var ram_range = "0, " + $(".ram-input").prop("max");
  $(".cpu-count-slider").data("slider-range", cpu_count_range);
  $(".ram-slider").data("slider-range", ram_range);

  $(".vm-slider").simpleSlider();
  $(".cpu-priority-slider").bind("slider:changed", function (event, data) {
    var value = data.value + 0;

    $('.cpu-priority-input option[value="' + value + '"]').attr("selected", "selected");
  });

  $(".cpu-priority-input").change(function() {
    var val = $(":selected", $(this)).val();
    $(".cpu-priority-slider").simpleSlider("setValue", val);
  });

  $(".cpu-count-slider").bind("slider:changed", function (event, data) {
    var value = data.value + 0;
    $(".cpu-count-input").val(parseInt(value));
  });

  $(".cpu-count-input").bind("input", function() {
    var val = parseInt($(this).val());
    if(!val) return;
    $(".cpu-count-slider").simpleSlider("setValue", val);
  });


  var ram_fire = false;
  $(".ram-slider").bind("slider:changed", function (event, data) {
    if(ram_fire) {
      ram_fire = false;
      return;
    }

    var value = data.value + 0;
    $(".ram-input").val(value);
  });

  $(".ram-input").bind("input", function() {
    var val = $(this).val();
    ram_fire = true;
    $(".ram-slider").simpleSlider("setValue", parseInt(val));
  });

  setDefaultSliderValues();

  $(".cpu-priority-slider").simpleSlider("setDisabled", $(".cpu-priority-input").prop("disabled"));
  $(".cpu-count-slider").simpleSlider("setDisabled", $(".cpu-count-input").prop("disabled"));
  $(".ram-slider").simpleSlider("setDisabled", $(".ram-input").prop("disabled"));
}

function setDefaultSliderValues() {
  $(".cpu-priority-input").trigger("change");
  $(".ram-input, .cpu-count-input").trigger("input");
}


/* deletes the VM with the pk
 * if dir is true, then redirect to the dashboard landing page
 * else it adds a success message */
function deleteObject(data) {
  $.ajax({
    type: 'POST',
    data: {'redirect': data.redirect},
    url: data.url,
    headers: {"X-CSRFToken": getCookie('csrftoken')},
    success: function(re, textStatus, xhr) {
      if(!data.redirect) {
        selected = [];
        addMessage(re.message, 'success');
        if(data.type === "disk") {
          // no need to remove them from DOM
          $('a[data-disk-pk="' + data.pk + '"]').parent("li").fadeOut();
          $('a[data-disk-pk="' + data.pk + '"]').parent("h4").fadeOut();
        }
        else {
          $('a[data-'+data.type+'-pk="' + data.pk + '"]').closest('tr').fadeOut(function() {
            $(this).remove();
          });
        }
      } else {
        window.location.replace('/dashboard');
      }
    },
    error: function(xhr, textStatus, error) {
      addMessage('Uh oh :(', 'danger');
    }
  });
}

function massDeleteVm(data) {
  f = function() {
    selected = [];
    // reset group buttons
    $('.vm-list-group-control a').attr('disabled', true);
    $(this).remove();
  };
  $.ajax({
      traditional: true,
      url: data.url,
      headers: {"X-CSRFToken": getCookie('csrftoken')},
      type: 'POST',
      data: {'vms': data.data.v},
      success: function(re, textStatus, xhr) {
        for(var i=0; i< data.data.v.length; i++)
          $('.vm-list-table tbody tr[data-vm-pk="' + data.data.v[i] + '"]').fadeOut(500, f);
        addMessage(re.message, 'success');
      },
      error: function(xhr, textStatus, error) {
        // TODO this
      }
    });
}


function addMessage(text, type) {
  $('body').animate({scrollTop: 0});
  div = '<div style="display: none;" class="alert alert-' + type + '">' + text + '</div>';
  $('.messagelist').html('').append(div);
  var div = $('.messagelist div').fadeIn();
  setTimeout(function() {
    $(div).fadeOut();
  }, 9000);
}


function addModalConfirmation(func, data) {
  $.ajax({
    type: 'GET',
    url: data.url,
    data: jQuery.param(data.data),
    success: function(result) {
      $('body').append(result);
      $('#confirmation-modal').modal('show');
      $('#confirmation-modal').on('hidden.bs.modal', function() {
        $('#confirmation-modal').remove();
      });
      $('#confirmation-modal-button').click(function() {
        func(data);
        $('#confirmation-modal').modal('hide');
      });
    }
  });
}

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


/* no js compatibility */
function noJS() {
  $('.no-js-hidden').show();
  $('.js-hidden').hide();
}
