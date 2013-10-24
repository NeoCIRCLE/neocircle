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

function vmCreateTemplateChange(new_this) {
  this.value = new_this.value;
  if(this.value < 0) return;
  $.ajax({
    url: '/dashboard/template/' + this.value,
    type: 'GET',
    success: function(data, textStatus, xhr) {
      if(xhr.status == 200) {
       // set sliders
        $('#cpu-priority-slider').simpleSlider("setValue", data['priority']);
        $('#cpu-count-slider').simpleSlider("setValue", data['num_cores']);
        $('#ram-slider').simpleSlider("setValue", data['ram_size']);

        $('#vm-create-network-list').html('');
        for(var n = 0; n<data['network'].length; n++) {
          nn = data['network'][n]
          $('#vm-create-network-list').append(
              vmCreateNetworkLabel(nn.vlan_pk, nn.vlan, nn.managed)
          );
        }
      }
    }
  });
}

function vmCreateNetworkLabel(pk, name, managed) {
  return '<span id="vlan-' + pk + '" class="label label-' +  (managed ? 'primary' : 'default')  + '"><i class="icon-' + (managed ? 'globe' : 'link') + '"></i> ' + name + ' <a href="#" class="hover-black vm-create-remove-network"><i class="icon-remove-sign"></i></a></span> ';
}


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
  
  $('#vm-create-template-select').change(function() {
    vmCreateTemplateChange(this);
  });
 
  $('#vm-create-network-add-button').click(function() {
    var option = $('#vm-create-network-add-select :selected');
    if(option.val() > 0) {
      if ($('#vm-create-network-list').children('span').length < 1) { 
        $('#vm-create-network-list').html('');
      }  
      $('#vm-create-network-list').append(
        vmCreateNetworkLabel(option.val(), option.text(), true)
      );
      $('option:selected', $('#vm-create-network-add-select')).remove();
    }

    return false;
  });

  // event for network remove button (icon, X)
  // TODO still not the right place
  $('body').on('click', '.vm-create-remove-network', function() {
    var vlan_pk = ($(this).parent('span').prop('id')).replace('vlan-', '');
    $(this).parent('span').fadeOut(500, function() { 
      $(this).remove(); 
      var vlan_name = $(this).text();

      $('#vm-create-network-add-select').append($('<option>', {
        value: vlan_pk,
        text: vlan_name
      }));

      if ($('#vm-create-network-list').children('span').length < 1) {
        $('#vm-create-network-list').append('Not added to any network!');
      }
    });
    return false;
  });

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
