$(function () {
  $('.vm-create').click(function(e) {
    $.ajax({
      type: 'GET',
      url: '/dashboard/vm/create/', 
      success: function(data) { 
        $('body').append(data);
        vmCreateLoaded();
        addSliderMiscs();
        $('#vm-create-modal').modal('show');
        $('#vm-create-modal').on('hidden.bs.modal', function() {
          $('#vm-create-modal').remove();
        });
      }
    });
    return false;
  });
  $('[href=#vm-graph-view]').click(function (e) {
    $('#vm-list-view').hide();
    $('#vm-graph-view').show();
    $('[href=#vm-list-view]').removeClass('disabled');
    $('[href=#vm-graph-view]').addClass('disabled');
    e.stopImmediatePropagation();
    return false;
  });
  $('[href=#vm-list-view]').click(function (e) {
    $('#vm-graph-view').hide();
    $('#vm-list-view').show();
    $('[href=#vm-list-view]').addClass('disabled');
    $('[href=#vm-graph-view]').removeClass('disabled');
    e.stopImmediatePropagation();
    return false;
  }).addClass('disabled');
  $('[title]').tooltip();
  $(':input[title]').tooltip({trigger: 'focus', placement: 'auto right'});
  $(".knob").knob();

  $('[data-toggle="pill"]').click(function() {
    window.location.hash = $(this).attr('href');
  });

  if (window.location.hash)
    $("a[href=" + window.location.hash +"]").tab('show');

  addSliderMiscs();

  /* for VM removes buttons */
  $('.vm-delete').click(function() {
    var vm_pk = $(this).data('vm-pk');
    text = "Are you sure you want to delete this VM?";
    var dir = window.location.pathname.indexOf('list') == -1;
    addModalConfirmation(text, vm_pk, deleteVm, dir);
    return false;
  });
});

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
function deleteVm(pk, dir) {
  $.ajax({
    type: 'POST',
    data: {'redirect': dir},
    url: '/dashboard/vm/delete/' + pk + '/',
    headers: {"X-CSRFToken": getCookie('csrftoken')}, 
    success: function(data, textStatus, xhr) { 
      if(!dir) {
        selected = [];
        addMessage(data['message'], 'success');
        $('a[data-vm-pk="' + pk + '"]').closest('tr').fadeOut(function() {
          $(this).remove();  
        });
      } else {
        window.location.replace('/dashboard');
      }
    },
    error: function(xhr, textStatus, error) {
      addMessage('Uh oh :(', 'danger')
    }
  });
}

function massDeleteVm() {
  $.ajax({                                                                
      traditional: true,                                                    
      url: '/dashboard/vm/mass-delete/',                                    
      headers: {"X-CSRFToken": getCookie('csrftoken')},                     
      type: 'POST',                                                         
      data: {'vms': collectIds(selected)},                                  
      success: function(data, textStatus, xhr) {                            
        for(var i=0; i< selected.length; i++)                               
          $('.vm-list-table tbody tr').eq(selected[i]).fadeOut(500, function() {
            // reset group buttons                                          
            selected = []                                                   
            $('.vm-list-group-control a').attr('disabled', true);           
            $(this).remove();                                               
          }); 
        addMessage(data['message'], 'success');                         
      },                                                                    
      error: function(xhr, textStatus, error) {                             
        // TODO this                                                        
      }                                                                     
    });          
}


function addMessage(text, type) {
  div = '<div style="display: none;" class="alert alert-' + type + '">' + text + '</div>';
  $('.messagelist').html('').append(div);
  $('.messagelist div').fadeIn();
}


function addModalConfirmation(text, data, func, dir) {
  $.ajax({
    type: 'GET',
    url: '/dashboard/vm/delete/' + data + '/',
    data: {'text': text},
    success: function(result) {
      $('body').append(result);
      $('#confirmation-modal').modal('show');
      $('#confirmation-modal').on('hidden.bs.modal', function() {
        $('#confirmation-modal').remove();
      });
      $('#confirmation-modal-button').click(function() {
        func(data, dir);
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
