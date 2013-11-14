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
  
  if (window.location.hash)
    $("a[href=" + window.location.hash +"]").tab('show');

  addSliderMiscs();
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

function addMessage(text, type) {
  div = '<div style="display: none;" class="alert alert-' + type + '">' + text + '</div>';
  $('.messagelist').html('').append(div);
  $('.messagelist div').fadeIn();
}


function addConfirmationModal(text, func) {

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
