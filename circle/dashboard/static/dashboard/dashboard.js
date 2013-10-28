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

  vmCreateLoaded();
  addSliderMiscs();
});

function addSliderMiscs() {
  $("[data-slider]").each(function() {
    if($(this).css('display') != "none") 
      $(this).simpleSlider();
  });

  //slider only has background with this ...
  //var js = document.createElement('script');
  //js.src = '/static/dashboard/loopj-jquery-simple-slider-fa64f59/js/simple-slider.min.js'; 
  //document.getElementsByTagName('head')[0].appendChild(js);


  $("[data-slider]")                                                        
    .each(function () {                                                     
      var input = $(this);                                                  
      $("<span>")                                                           
        .addClass("output")                                                 
        .html($(this).val())                                                
        .insertAfter(input);                                                
    })                                                                      
    .bind("slider:ready slider:changed", function (event, data) {           
      $(this)                                                               
        .nextAll(".output:first")                                           
          .html(data.value.toFixed(3));                                     
    });

  $("[data-mark]").each(function () {                                                 
    var value=$(this).attr('data-mark').parseFloat();               
  }); 
}
