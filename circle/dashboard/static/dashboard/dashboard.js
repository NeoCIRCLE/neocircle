$(function () {
  $('.vm-create').click(function(e) {
    $.ajax({
      type: 'GET',
      url: '/dashboard/vm/create/', 
      success: function(data) { 
        $('body').append(data);
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

        /* clear selection */
        $('select[id^="vm-create-network-add"], select[id$="managed"]').find('option').prop('selected', false);

        /* append vlans from InterfaceTemplates */
        $('#vm-create-network-list').html('');
        var added_vlans = []
        for(var n = 0; n<data['network'].length; n++) {
          nn = data['network'][n]
          $('#vm-create-network-list').append(
              vmCreateNetworkLabel(nn.vlan_pk, nn.vlan, nn.managed)
          );
          
          $('#vm-create-network-add-' + (nn.managed ? '' : 'un') + 'managed option[value="' + nn.vlan_pk + '"]').prop('selected', true);
          added_vlans.push(nn.vlan_pk);
        }

        /* remove already added vlans from dropdown or add new ones */
        $('#vm-create-network-add-select').html('');
        for(var i=0; i < vlans.length; i++)
          if(added_vlans.indexOf(vlans[i].pk) == -1)
            $('#vm-create-network-add-select').append($('<option>', {
              value: vlans[i].pk,                                                     
              text: vlans[i].name                                                     
            }));
       
        /* enalbe the network add button if there are not added vlans */
        if(added_vlans.length != vlans.length) {
          $('#vm-create-network-add-button').attr('disabled', false);
        } else {
          $('#vm-create-network-add-select').html('<option value="-1">We are out of &lt;options&gt; hehe</option>');
          $('#vm-create-network-add-button').attr('disabled', true);
        }
      }
    }
  });
}

function vmCreateNetworkLabel(pk, name, managed) {
  return '<span id="vlan-' + pk + '" class="label label-' +  (managed ? 'primary' : 'default')  + '"><i class="icon-' + (managed ? 'globe' : 'link') + '"></i> ' + name + ' <a href="#" class="hover-black vm-create-remove-network"><i class="icon-remove-sign"></i></a></span> ';
}


var vlans = [];
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
 
  /* add network */
  $('#vm-create-network-add-button').click(function() {
    var vlan_pk = $('#vm-create-network-add-select :selected').val();
    var managed = $('#vm-create-network-add-checkbox-managed').prop('checked');
    var name = $('#vm-create-network-add-select :selected').text();

    if ($('#vm-create-network-list').children('span').length < 1) { 
      $('#vm-create-network-list').html('');
    }  
    $('#vm-create-network-list').append(
      vmCreateNetworkLabel(vlan_pk, name, managed)
    );

    /* select the network from the managed/unmanaged multiple select */
    if(managed) {
      $('#vm-create-network-add-managed option[value="' + vlan_pk + '"]').prop('selected', true);
    } else {
      $('#vm-create-network-add-unmanaged option[value="' + vlan_pk + '"]').prop('selected', true);
    }
    /* remove the network from select */
    $('option:selected', $('#vm-create-network-add-select')).remove();
    
    /* add dummy text if no more networks are available */
    if($('#vm-create-network-add-select option').length < 1) {
      $('#vm-create-network-add-button').attr('disabled', true);
      $('#vm-create-network-add-select').html('<option value="-1">We are out of &lt;options&gt; hehe</option>');
    }

    return false;
  });

  /* remove network */
  // event for network remove button (icon, X)
  // TODO still not the right place (wrong file ...)
  $('body').on('click', '.vm-create-remove-network', function() {
    var vlan_pk = ($(this).parent('span').prop('id')).replace('vlan-', '')
    // if it's "blue" then it's managed, kinda not cool
    var managed = $(this).parent('span').hasClass('label-primary');

    $(this).parent('span').fadeOut(500, function() {
      /* if ther are no more vlans disabled the add button */
      if($('#vm-create-network-add-select option')[0].value == -1) {   
        $('#vm-create-network-add-button').attr('disabled', false);            
        $('#vm-create-network-add-select').html('');
      }
      
      /* remove the network label */
      $(this).remove(); 

      var vlan_name = $(this).text();
      $('#vm-create-network-add-select').append($('<option>', {
        value: vlan_pk,
        text: vlan_name
      }));

      /* remove the selection from the multiple select */
      $('#vm-create-network-add-' + (managed ? '' : 'un') + 'managed option[value="' + vlan_pk + '"]').prop('selected', false);
      if ($('#vm-create-network-list').children('span').length < 1) {
        $('#vm-create-network-list').append('Not added to any network!');
      }
    });
    return false;
  });

  /* copy networks from hidden select */
  $('#vm-create-network-add-select').html($('#vm-create-network-add-managed').html());


  /* build up network list */
  $('#vm-create-network-add-select option').each(function() {
    vlans.push({
      'name': $(this).text(),
      'pk': parseInt($(this).val())
    });
  });

  /* no js compatibility */
  $('.no-js-hidden').show();
  $('.js-hidden').hide();


  /* slider things */
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
