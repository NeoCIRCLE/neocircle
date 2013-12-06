var vlans = [];
var disks = [];

$(function() {
  nodeCreateLoaded();
});

function nodeCreateLoaded() {
  $('.node-create-advanced').hide();
  $('.node-create-advanced-btn').click(function() {
    $('.vm-create-advanced').stop().slideToggle();
    if ($('.node-create-advanced-icon').hasClass('icon-caret-down')) {
      $('.node-create-advanced-icon').removeClass('icon-caret-down').addClass('icon-caret-up');
    } else { 
      $('.node-create-advanced-icon').removeClass('icon-caret-up').addClass('icon-caret-down');
    } 
  });
  
  $('#node-create-template-select').change(function() {
    nodeCreateTemplateChange(this);
  });
 
  /* network thingies */

  /* add network */
  $('#node-create-network-add-button').click(function() {
    var vlan_pk = $('#node-create-network-add-select :selected').val();
    var managed = $('#node-create-network-add-checkbox-managed').prop('checked');
    var name = $('#node-create-network-add-select :selected').text();

    if ($('#node-create-network-list').children('span').length < 1) { 
      $('#node-create-network-list').html('');
    }  
    $('#node-create-network-list').append(
     nodeCreateNetworkLabel(vlan_pk, name, managed)
    );

    /* select the network from the managed/unmanaged multiple select */
    if(managed) {
      $('#node-create-network-add-managed option[value="' + vlan_pk + '"]').prop('selected', true);
    } else {
      $('#node-create-network-add-unmanaged option[value="' + vlan_pk + '"]').prop('selected', true);
    }

    $('option:selected', $('#node-create-network-add-select')).remove();
    
    /* add dummy text if no more networks are available */
    if($('#node-create-network-add-select option').length < 1) {
      $('#node-create-network-add-button').attr('disabled', true);
      $('#node-create-network-add-select').html('<option value="-1">We are out of &lt;options&gt; hehe</option>');
    }

    return false;
  });

  /* remove network */
  // event for network remove button (icon, X)
  $('body').on('click', '.node-create-remove-network', function() {
    var vlan_pk = ($(this).parent('span').prop('id')).replace('vlan-', '')
    // if it's "blue" then it's managed, kinda not cool
    var managed = $(this).parent('span').hasClass('label-primary');

    $(this).parent('span').fadeOut(500, function() {
      /* if ther are no more vlans disabled the add button */
      if($('#node-create-network-add-select option')[0].value == -1) {   
        $('#node-create-network-add-button').attr('disabled', false);            
        $('#node-create-network-add-select').html('');
      }
      
      /* remove the network label */
      $(this).remove(); 

      var vlan_name = $(this).text();
      $('#node-create-network-add-select').append($('<option>', {
        value: vlan_pk,
        text: vlan_name
      }));

      /* remove the selection from the multiple select */
      $('#node-create-network-add-' + (managed ? '' : 'un') + 'managed option[value="' + vlan_pk + '"]').prop('selected', false);
      if ($('#node-create-network-list').children('span').length < 1) {
        $('#node-create-network-list').append('Not added to any network!');
      }
    });
    return false;
  });

  /* copy networks from hidden select */
  $('#node-create-network-add-select').html($('#node-create-network-add-managed').html());


  /* build up network list */
  $('#node-create-network-add-select option').each(function() {
    vlans.push({
      'name': $(this).text(),
      'pk': parseInt($(this).val())
    });
  });

  /* ----- end of networks thingies ----- */


  /* add disk */
  $('#node-create-disk-add-button').click(function() {
    var disk_pk = $('#node-create-disk-add-select :selected').val();
    var name = $('#node-create-disk-add-select :selected').text();

    if ($('#node-create-disk-list').children('span').length < 1) { 
      $('#node-create-disk-list').html('');
    }  
    $('#node-create-disk-list').append(
      nodeCreateDiskLabel(disk_pk, name)
    );

    /* select the disk from the multiple select */
    $('#node-create-disk-add-form option[value="' + disk_pk + '"]').prop('selected', true);

    $('option:selected', $('#node-create-disk-add-select')).remove();
    
    /* add dummy text if no more disks are available */
    if($('#node-create-disk-add-select option').length < 1) {
      $('#node-create-disk-add-button').attr('disabled', true);
      $('#node-create-disk-add-select').html('<option value="-1">We are out of &lt;options&gt; hehe</option>');
    }

    return false;
  });


  /* remove disk */
  // event for disk remove button (icon, X)
  $('body').on('click', '.node-create-remove-disk', function() {
    var disk_pk = ($(this).parent('span').prop('id')).replace('vlan-', '')

    $(this).parent('span').fadeOut(500, function() {
      /* if ther are no more disks disabled the add button */
      if($('#node-create-disk-add-select option')[0].value == -1) {   
        $('#node-create-disk-add-button').attr('disabled', false);            
        $('#node-create-disk-add-select').html('');
      }
      
      /* remove the disk label */
      $(this).remove(); 

      var disk_name = $(this).text();
      $('#node-create-disk-add-select').append($('<option>', {
        value: disk_pk,
        text: disk_name
      }));

      /* remove the selection from the multiple select */
      $('#node-create-disk-add-form option[value="' + disk_pk + '"]').prop('selected', false);
      if ($('#node-create-disk-list').children('span').length < 1) {
        $('#node-create-disk-list').append('No disks are added!');
      }
    });
    return false;
  });

  /* copy disks from hidden select */
  $('#node-create-disk-add-select').html($('#node-create-disk-add-form').html());


  /* build up disk list */
  $('#node-create-disk-add-select option').each(function() {
    disks.push({
      'name': $(this).text(),
      'pk': parseInt($(this).val())
    });
  });

  /* add button */
  $('#node-create-submit').click(function() {
    $.ajax({
      url: '/dashboard/node/create/',
      headers: {"X-CSRFToken": getCookie('csrftoken')},
      type: 'POST',
      data: $('form').serialize(),
      success: function(data, textStatus, xhr) {
        if(data.pk) {
          window.location.replace('/dashboard/node/' + data.pk + '/#activity');
        }
      },
      error: function(xhr, textStatus, error) {
        if (xhr.status == 500) {
          alert("uhuhuhuhuhuh");
        } else {
          alert("unknown error");
        }
      }
    });
    return false;
  });

  /* no js compatibility */
  $('.no-js-hidden').show();
  $('.js-hidden').hide();
}

function nodeCreateTemplateChange(new_this) {
  this.value = new_this.value;
  if(this.value < 0) return;
  $.ajax({
    url: '/dashboard/template/' + this.value,
    type: 'GET',
    success: function(data, textStatus, xhr) {
      if(xhr.status == 200) {
        // set sliders
        $('#node-cpu-priority-slider').slider("setValue", data['priority']);
        $('#node-cpu-count-slider').slider("setValue", data['num_cores']);
        $('#node-ram-size-slider').slider("setValue", data['ram_size']);
        
        /* slider doesn't have change event ........................ */
        refreshSliders();

        /* clear selections */
        $('select[id^="node-create-network-add"], select[id$="managed"]').find('option').prop('selected', false);
         $('#node-create-disk-add-form').find('option').prop('selected', false);

        /* append vlans from InterfaceTemplates */
        $('#vm-create-network-list').html('');
        var added_vlans = []
        for(var n = 0; n<data['network'].length; n++) {
          nn = data['network'][n]
          $('#node-create-network-list').append(
              nodeCreateNetworkLabel(nn.vlan_pk, nn.vlan, nn.managed)
          );
          
          $('#node-create-network-add-' + (nn.managed ? '' : 'un') + 'managed option[value="' + nn.vlan_pk + '"]').prop('selected', true);
          added_vlans.push(nn.vlan_pk);
        }

        /* remove already added vlans from dropdown or add new ones */
        $('#node-create-network-add-select').html('');
        for(var i=0; i < vlans.length; i++)
          if(added_vlans.indexOf(vlans[i].pk) == -1)
            $('#node-create-network-add-select').append($('<option>', {
              value: vlans[i].pk,                                                     
              text: vlans[i].name                                                     
            }));
       
        /* enalbe the network add button if there are not added vlans */
        if(added_vlans.length != vlans.length) {
          $('#node-create-network-add-button').attr('disabled', false);
        } else {
          $('#node-create-network-add-select').html('<option value="-1">We are out of &lt;options&gt; hehe</option>');
          $('#node-create-network-add-button').attr('disabled', true);
        }


        /* append disks */
        $('#node-create-disk-list').html('');
        var added_disks = []
        for(var d = 0; d<data['disks'].length; d++) {
          dd = data['disks'][d]
          $('#node-create-disk-list').append(
              nodeCreateDiskLabel(dd.pk, dd.name)
          );
          
          $('#node-create-disk-add-form option[value="' + dd.pk + '"]').prop('selected', true);
          added_disks.push(dd.pk);
        }

        /* remove already added disks from dropdown or add new ones */
        $('#node-create-disk-add-select').html('');
        for(var i=0; i < disks.length; i++)
          if(added_disks.indexOf(disks[i].pk) == -1)
            $('#node-create-disk-add-select').append($('<option>', {
              value: disks[i].pk,                                                     
              text: disks[i].name                                                     
            }));
       
        /* enalbe the disk add button if there are not added disks */
        if(added_disks.length != disks.length) {
          $('#node-create-disk-add-button').attr('disabled', false);
        } else {
          $('#node-create-disk-add-select').html('<option value="-1">We are out of &lt;options&gt; hehe</option>');
          $('#node-create-disk-add-button').attr('disabled', true);
        }
      }
    }
  });
}

function vmCreateNetworkLabel(pk, name, managed) {
  return '<span id="vlan-' + pk + '" class="label label-' +  (managed ? 'primary' : 'default')  + '"><i class="icon-' + (managed ? 'globe' : 'link') + '"></i> ' + name + ' <a href="#" class="hover-black node-create-remove-network"><i class="icon-remove-sign"></i></a></span> ';
}


function vmCreateDiskLabel(pk, name) {
  return '<span id="vlan-' + pk + '" class="label label-primary"><i class="icon-file"></i> ' + name + ' <a href="#" class="hover-black node-create-remove-disk"><i class="icon-remove-sign"></i></a></span> ';
}


