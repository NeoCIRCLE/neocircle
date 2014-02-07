var vlans = [];
var disks = [];

$(function() {
  vmCreateLoaded();
});

function vmCreateLoaded() {
  $('.vm-create-advanced').hide();
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
    var managed = $('#vm-create-network-add-select :selected').data('managed');
    var name = $('#vm-create-network-add-select :selected').text();
    // remove the hex chars
    name = name.substring(name.indexOf(" "), name.length);

    if ($('#vm-create-network-list').children('span').length < 1) { 
      $('#vm-create-network-list').html('');
    }  
    $('#vm-create-network-list').append(
      vmCreateNetworkLabel(vlan_pk, name, managed)
    );
    
    /* select the network in the hidden network select */
    $('#vm-create-network-add-vlan option[value="' + vlan_pk + '"]').prop('selected', true);

    $('option:selected', $('#vm-create-network-add-select')).remove();
    
    /* add dummy text if no more networks are available */
    if($('#vm-create-network-add-select option').length < 1) {
      $('#vm-create-network-add-button').attr('disabled', true);
      $('#vm-create-network-add-select').html('<option value="-1">No more networks!</option>');
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

      var html = '<option data-managed="' + (managed ? 1 : 0) + '" value="' + vlan_pk + '">'+ 
                 (managed ? "&#xf0ac;": "&#xf0c1;") + vlan_name + '</option>';
      $('#vm-create-network-add-select').append(html);

      /* remove the selection from the multiple select */
      $('#vm-create-network-add-vlan option[value="' + vlan_pk + '"]').prop('selected', false);
      if ($('#vm-create-network-list').children('span').length < 1) {
        $('#vm-create-network-list').append('Not added to any network!');
      }
    });
    return false;
  });

  /* copy networks from hidden select */
  $('#vm-create-network-add-vlan option').each(function() {
    var managed = $(this).text().indexOf("mana") == 0;
    var text = $(this).text();
    var pk = $(this).val();
    if(managed) {
      text = text.replace("managed -", "&#xf0ac;");
    } else {
      text = text.replace("unmanaged -", "&#xf0c1;");
    }
    var html = '<option data-managed="' + (managed ? 1 : 0) + '" value="' + pk + '">' + text + '</option>';
    $('#vm-create-network-add-select').append(html);
  });


  /* build up network list */
  $('#vm-create-network-add-vlan option').each(function() {
    vlans.push({
      'name': $(this).text().replace("unmanaged -", "&#xf0c1;").replace("managed -", "&#xf0ac;"),
      'pk': parseInt($(this).val()),
      'managed': $(this).text().indexOf("mana") == 0,
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

  /* add button */
  $('#vm-create-submit').click(function() {
    $.ajax({
      url: '/dashboard/vm/create/',
      headers: {"X-CSRFToken": getCookie('csrftoken')},
      type: 'POST',
      data: $('form').serialize(),
      success: function(data, textStatus, xhr) {
        if(data.redirect) {
          window.location.replace(data.redirect + '#activity');
        }
        else {
            var r = $('#create-modal'); r.next('div').remove(); r.remove();
            $('body').append(data);
            vmCreateLoaded();
            addSliderMiscs();
            $('#create-modal').modal('show');
            $('#create-modal').on('hidden.bs.modal', function() {
                $('#create-modal').remove();
            });
        }
      },
      error: function(xhr, textStatus, error) {
        var r = $('#create-modal'); r.next('div').remove(); r.remove();
        
        if (xhr.status == 500) {
          addMessage("500 Internal Server Error", "danger");
        } else {
          addMessage(xhr.status + " Unknown Error", "danger");
        }
      }
    });
    return false;
  });

  /* for no js stuff */
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
        $('#vm-cpu-priority-slider').slider("setValue", data['priority']);
        $('#vm-cpu-count-slider').slider("setValue", data['num_cores']);
        $('#vm-ram-size-slider').slider("setValue", data['ram_size']);
        
        /* slider doesn't have change event ........................ */
        refreshSliders();

        /* clear selections */
        $("#vm-create-network-add-vlan").find('option').prop('selected', false);
        $('#vm-create-disk-add-form').find('option').prop('selected', false);

        /* clear the network select */
        $("#vm-create-network-add-select").html('');

        /* append vlans from InterfaceTemplates */
        $('#vm-create-network-list').html("");
        var added_vlans = []
        for(var n = 0; n<data['network'].length; n++) {
          nn = data['network'][n]
          $('#vm-create-network-list').append(
              vmCreateNetworkLabel(nn.vlan_pk, nn.vlan, nn.managed)
          );
          
          $('#vm-create-network-add-vlan option[value="' + nn.vlan_pk + '"]').prop('selected', true);
          added_vlans.push(nn.vlan_pk);
        }

        /* remove already added vlans from dropdown or add new ones */
        $('#vm-create-network-add-select').html('');
        // this is working because the vlans array already has the icon's hex code
        for(var i=0; i < vlans.length; i++)
          if(added_vlans.indexOf(vlans[i].pk) == -1) {
            var html = '<option data-managed="' + (vlans[i].managed ? 1 : 0) + '" value="' + vlans[i].pk + '">' + vlans[i].name + '</option>';
            $('#vm-create-network-add-select').append(html);
          }
       
        /* enable the network add button if there are not added vlans */
        if(added_vlans.length != vlans.length) {
          $('#vm-create-network-add-button').attr('disabled', false);
        } else {
          $('#vm-create-network-add-select').html('<option value="-1">No more networks!</option>');
          $('#vm-create-network-add-button').attr('disabled', true);
        }

        /* if there are no added vlans print it out */
        if(added_vlans.length < 1) {
          $('#vm-create-network-list').html("Not added to any network!");
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
       
        /* enable the disk add button if there are not added disks */
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
