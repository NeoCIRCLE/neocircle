var vlans = [];
var disks = [];
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
 
  /* network thingies */

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

  /* ----- end of networks thingies ----- */


  /* add disk */
  $('#vm-create-disk-add-button').click(function() {
    var disk_pk = $('#vm-create-disk-add-select :selected').val();
    var name = $('#vm-create-disk-add-select :selected').text();

    if ($('#vm-create-disk-list').children('span').length < 1) { 
      $('#vm-create-disk-list').html('');
    }  
    $('#vm-create-disk-list').append(
      vmCreateDiskLabel(disk_pk, name)
    );

    /* select the disk from the multiple select */
    $('#vm-create-disk-add-form option[value="' + disk_pk + '"]').prop('selected', true);

    $('option:selected', $('#vm-create-disk-add-select')).remove();
    
    /* add dummy text if no more disks are available */
    if($('#vm-create-disk-add-select option').length < 1) {
      $('#vm-create-disk-add-button').attr('disabled', true);
      $('#vm-create-disk-add-select').html('<option value="-1">We are out of &lt;options&gt; hehe</option>');
    }

    return false;
  });


  /* remove disk */
  // event for disk remove button (icon, X)
  $('body').on('click', '.vm-create-remove-disk', function() {
    var disk_pk = ($(this).parent('span').prop('id')).replace('vlan-', '')

    $(this).parent('span').fadeOut(500, function() {
      /* if ther are no more disks disabled the add button */
      if($('#vm-create-disk-add-select option')[0].value == -1) {   
        $('#vm-create-disk-add-button').attr('disabled', false);            
        $('#vm-create-disk-add-select').html('');
      }
      
      /* remove the disk label */
      $(this).remove(); 

      var disk_name = $(this).text();
      $('#vm-create-disk-add-select').append($('<option>', {
        value: disk_pk,
        text: disk_name
      }));

      /* remove the selection from the multiple select */
      $('#vm-create-disk-add-form option[value="' + disk_pk + '"]').prop('selected', false);
      if ($('#vm-create-disk-list').children('span').length < 1) {
        $('#vm-create-disk-list').append('No disks are added!');
      }
    });
    return false;
  });

  /* copy disks from hidden select */
  $('#vm-create-disk-add-select').html($('#vm-create-disk-add-form').html());


  /* build up disk list */
  $('#vm-create-disk-add-select option').each(function() {
    disks.push({
      'name': $(this).text(),
      'pk': parseInt($(this).val())
    });
  });
  /* no js compatibility */
  $('.no-js-hidden').show();
  $('.js-hidden').hide();
}

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

        /* clear selections */
        $('select[id^="vm-create-network-add"], select[id$="managed"]').find('option').prop('selected', false);
         $('#vm-create-disk-add-form').find('option').prop('selected', false);

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


        /* append disks */
        $('#vm-create-disk-list').html('');
        var added_disks = []
        for(var d = 0; d<data['disks'].length; d++) {
          dd = data['disks'][d]
          $('#vm-create-disk-list').append(
              vmCreateDiskLabel(dd.pk, dd.name)
          );
          
          $('#vm-create-disk-add-form option[value="' + dd.pk + '"]').prop('selected', true);
          added_disks.push(dd.pk);
        }

        /* remove already added disks from dropdown or add new ones */
        $('#vm-create-disk-add-select').html('');
        for(var i=0; i < disks.length; i++)
          if(added_disks.indexOf(disks[i].pk) == -1)
            $('#vm-create-disk-add-select').append($('<option>', {
              value: disks[i].pk,                                                     
              text: disks[i].name                                                     
            }));
       
        /* enalbe the disk add button if there are not added disks */
        if(added_disks.length != disks.length) {
          $('#vm-create-disk-add-button').attr('disabled', false);
        } else {
          $('#vm-create-disk-add-select').html('<option value="-1">We are out of &lt;options&gt; hehe</option>');
          $('#vm-create-disk-add-button').attr('disabled', true);
        }
      }
    }
  });
}

function vmCreateNetworkLabel(pk, name, managed) {
  return '<span id="vlan-' + pk + '" class="label label-' +  (managed ? 'primary' : 'default')  + '"><i class="icon-' + (managed ? 'globe' : 'link') + '"></i> ' + name + ' <a href="#" class="hover-black vm-create-remove-network"><i class="icon-remove-sign"></i></a></span> ';
}


function vmCreateDiskLabel(pk, name) {
  return '<span id="vlan-' + pk + '" class="label label-primary"><i class="icon-file"></i> ' + name + ' <a href="#" class="hover-black vm-create-remove-disk"><i class="icon-remove-sign"></i></a></span> ';
}
