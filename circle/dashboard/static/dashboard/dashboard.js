$(function () {
  $('.vm-create').click(function(e) {
    $.ajax({
      type: 'GET',
      url: '/dashboard/vm/create/', 
      success: function(data) { 
        // TODO this is still ugly
        var html = '<div class="modal fade" id="vm-create-modal" tabindex="-1" role="dialog">' +
                    '<div class="modal-dialog">' +
                      '<div class="modal-content">' +
                        '<div class="modal-header">' +
                          '<button type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>' +
                          '<h4 class="modal-title">Create VM</h4>' +
                        '</div>' +
                        '<div class="modal-body"> ' +
                          data +
                        '</div>' +
                      /*'<div class="modal-footer">' +
                          '<button type="button" class="btn btn-default" data-dismiss="modal">Close</button>' +
                          '<button type="button" class="btn btn-primary">Save changes</button>' +
                        '</div>' + */
                      '</div><!-- /.modal-content -->' +
                     '</div><!-- /.modal-dialog -->' +
                    '</div>';

        $('body').append(html);
        vmCreateLoaded();
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
});

function vmCreateLoaded() {
  // temporarily disable for testing
  //$('.vm-create-advanced').hide();
  $('.vm-create-advanced-btn').click(function() {
    $('.vm-create-advanced').stop().slideToggle();
    if ($('.vm-create-advanced-icon').hasClass('icon-caret-down')) {
      $('.vm-create-advanced-icon').removeClass('icon-caret-down').addClass('icon-caret-up');
    } else { 
      $('.vm-create-advanced-icon').removeClass('icon-caret-up').addClass('icon-caret-down');
    } 
  });
  
 
  $("[data-slider]").each(function() {
    if($(this).css('display') != "none") 
      $(this).simpleSlider();
  });

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
