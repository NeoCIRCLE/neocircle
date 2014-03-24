$(function () {
  $('.vm-create').click(function(e) {
    var template = $(this).data("template");
    $.ajax({
      type: 'GET',
      url: '/dashboard/vm/create/' + (isNaN(template) ? '' : '?template=' + template), 
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
  $('.no-js-hidden').show();
  $('.js-hidden').hide();

  /* favourite star */
  $("#dashboard-vm-list").on('click', '.dashboard-vm-favourite', function(e) {
    var star = $(this).children("i");
    var pk = $(this).data("vm");
    if(star.hasClass("icon-star-empty")) {
      star.removeClass("icon-star-empty").addClass("icon-star");
      star.prop("title", "Unfavourite");
    } else {
      star.removeClass("icon-star").addClass("icon-star-empty");
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
  var my_vms = []
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
          });
        }
      });
      $.ajaxSetup( { "async": true } );
    }

    input = $("#dashboard-vm-search-input").val().toLowerCase();
    var search_result = []
    var html = '';
    for(var i in my_vms) {
      if(my_vms[i].name.indexOf(input) != -1) {
        search_result.push(my_vms[i]);
      }
    }
    search_result.sort(compareVmByFav);
    for(var i=0; i<5 && i<search_result.length; i++)
      html += generateVmHTML(search_result[i].pk, search_result[i].name, search_result[i].fav);
    if(search_result.length == 0)
      html += '<div class="list-group-item">No result</div>';
    $("#dashboard-vm-list").html(html);
    $('.title-favourite').tooltip({'placement': 'right'});

    // if there is only one result and ENTER is pressed redirect
    if(e.keyCode == 13 && search_result.length == 1) {
      window.location.href = "/dashboard/vm/" + search_result[0].pk + "/";
    }
    if(e.keyCode == 13 && search_result.length > 1 && input.length > 0) {
      window.location.href = "/dashboard/vm/list/?s=" + input;
    }
  });

  /* notification message toggle */
  $(document).on('click', ".notification-message-subject", function() {
    $(".notification-message-text", $(this).parent()).slideToggle();
    return false;
  });

  $("#notification-button a").click(function() {
      $('.notification-messages').load("/dashboard/notifications/");
  });
});

function generateVmHTML(pk, name, fav) {
  return '<a href="/dashboard/vm/' + pk + '/" class="list-group-item">' + 
          '<i class="icon-play-sign"></i> ' + name +
          '<div class="pull-right dashboard-vm-favourite" data-vm="' + pk +'">' + 
          '<i class="title-favourite icon-star' + (fav ? "" : "-empty") + ' text-primary" title="" data-original-title="' + 
          (fav ? "Un": "Mark as ") + 'favourite"></i>' +
          '</div>' + 
          '</a>';
}

function compareVmByFav(a, b) {
  if(a.fav && b.fav) {
    return a.pk < b.pk ? -1 : 1; 
  }
  if(a.fav) {
    return -1;
  }
  else
    return a.pk < b.pk ? -1 : 1; 
}

function addSliderMiscs() {
  $('.vm-slider').each(function() {  
    $("<span>").addClass("output").html($(this).val()).insertAfter($(this));
  });                                                                   
                                                                            
  $('.vm-slider').slider()                                              
  .on('slide', function(e) {                                            
    $(this).val(e.value);
    $(this).parent('div').nextAll("span").html(e.value)                 
  });

  refreshSliders();
}

// ehhh
function refreshSliders() {
  $('.vm-slider').each(function() {
    $(this).val($(this).slider().data('slider').getValue());
    $(this).parent('div').nextAll("span").html($(this).val());
  });
}

/* deletes the VM with the pk
 * if dir is true, then redirect to the dashboard landing page
 * else it adds a success message */
function deleteObject(data) {
  $.ajax({
    type: 'POST',
    data: {'redirect': data['redirect']},
    url: data['url'],
    headers: {"X-CSRFToken": getCookie('csrftoken')}, 
    success: function(re, textStatus, xhr) { 
      if(!data['redirect']) {
        selected = [];
        addMessage(re['message'], 'success');
        if(data.type === "disk") {
          // no need to remove them from DOM
          $('a[data-disk-pk="' + data.pk + '"]').parent("li").fadeOut();
          $('a[data-disk-pk="' + data.pk + '"]').parent("h4").fadeOut();
        } else { 
          $('a[data-'+data['type']+'-pk="' + data['pk'] + '"]').closest('tr').fadeOut(function() {
            $(this).remove();  
          });
        }
      } else {
        window.location.replace('/dashboard');
      }
    },
    error: function(xhr, textStatus, error) {
      addMessage('Uh oh :(', 'danger')
    }
  });
}

function massDeleteVm(data) {
  $.ajax({                                                                
      traditional: true,                                                    
      url: data['url'],                                    
      headers: {"X-CSRFToken": getCookie('csrftoken')},                     
      type: 'POST',                                                         
      data: {'vms': data['data']['v']},                                  
      success: function(re, textStatus, xhr) {                            
        for(var i=0; i< selected.length; i++)                               
          $('.vm-list-table tbody tr').eq(data['data']['selected'][i]).fadeOut(500, function() {
            // reset group buttons                                          
            selected = []                                                   
            $('.vm-list-group-control a').attr('disabled', true);           
            $(this).remove();                                               
          }); 
        addMessage(re['message'], 'success');                         
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
  $('.messagelist div').fadeIn();
}


function addModalConfirmation(func, data) {
  $.ajax({
    type: 'GET',
    url: data['url'],
    data: jQuery.param(data['data']),
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
