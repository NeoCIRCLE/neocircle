var vlans = [];
var disks = [];

$(function() {
  vmCustomizeLoaded();
});

function vmCreateLoaded() {
  $(".vm-create-template-details").hide();

  $(".vm-create-template-summary").click(function() {
    $(this).next(".vm-create-template-details").slideToggle();
  });

  $(".customize-vm").click(function() {
    var template = $(this).data("template-pk");
  
    $.get("/dashboard/vm/create/?template=" + template, function(data) {
        var r = $('#create-modal'); r.next('div').remove(); r.remove();
        $('body').append(data);
        vmCreateLoaded();
        addSliderMiscs();
        $('#create-modal').modal('show');
        $('#create-modal').on('hidden.bs.modal', function() {
            $('#create-modal').remove();
        });
    });
    return false;
  });
  
  /* start vm button clicks */
  $('.vm-create-start').click(function() {
    template = $(this).data("template-pk");
    $.ajax({
      url: '/dashboard/vm/create/',
      headers: {"X-CSRFToken": getCookie('csrftoken')},
      type: 'POST',
      data: {'template': template},
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

}

function vmCustomizeLoaded() {
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
    var raw_text = $(this).text();
    var pk = $(this).val();
    if(managed) {
      text = raw_text.replace("managed -", "&#xf0ac;");
    } else {
      text = raw_text.replace("unmanaged -", "&#xf0c1;");
    }
    var html = '<option data-managed="' + (managed ? 1 : 0) + '" value="' + pk + '">' + text + '</option>';
  
    if($('#vm-create-network-list span').length < 1) {
      $("#vm-create-network-list").html("");
    }
    if($(this).is(":selected")) {
      $("#vm-create-network-list").append(vmCreateNetworkLabel(pk, raw_text.replace("unmanaged -", "").replace("managed -", ""), managed));
    } else {
      $('#vm-create-network-add-select').append(html);
    }

  });

  // if all networks are added add a dummy and disable the add button
  if($("#vm-create-network-add-select option").length < 1) {
    $("#vm-create-network-add-select").html('<option value="-1">No more networks!</option>');
    $('#vm-create-network-add-button').attr('disabled', true);
  }

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
    var disk_pk = ($(this).parent('span').prop('id')).replace('disk-', '')

    $(this).parent('span').fadeOut(500, function() {
      /* remove the disk label */
      $(this).remove(); 

      var disk_name = $(this).text();
      
      /* remove the selection from the multiple select */
      $('#vm-create-disk-add-form option[value="' + disk_pk + '"]').prop('selected', false);
      if ($('#vm-create-disk-list').children('span').length < 1) {
        $('#vm-create-disk-list').append('No disks are added!');
      }
    });
    return false;
  });

  /* copy disks from hidden select */
  $('#vm-create-disk-add-form option').each(function() {
    var text = $(this).text();
    var pk = $(this).val();
    var html = '<option value="' + pk + '">' + text + '</option>';

    if($('#vm-create-disk-list span').length < 1) {
      $("#vm-create-disk-list").html("");
    }
    if($(this).is(":selected")) {
      $("#vm-create-disk-list").append(vmCreateDiskLabel(pk, text));
    } else {
      $('#vm-create-disk-add-select').append(html);
    }
  });

  /* build up disk list */
  $('#vm-create-disk-add-select option').each(function() {
    disks.push({
      'name': $(this).text(),
      'pk': parseInt($(this).val())
    });
  });

  /* start vm button clicks */
  $('#vm-create-customized-start').click(function() {
    $.ajax({
      url: '/dashboard/vm/create/',
      headers: {"X-CSRFToken": getCookie('csrftoken')},
      type: 'POST',
      data: $('form').serialize(),
      success: function(data, textStatus, xhr) {
        if(data.redirect) {
          /* it won't redirect to the same page */
          if(window.location.pathname == data.redirect) {
            window.location.reload();
          }
          window.location.href = data.redirect + '#activity';
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


function vmCreateNetworkLabel(pk, name, managed) {
  return '<span id="vlan-' + pk + '" class="label label-' +  (managed ? 'primary' : 'default')  + '"><i class="fa fa-' + (managed ? 'globe' : 'link') + '"></i> ' + name + ' <a href="#" class="hover-black vm-create-remove-network"><i class="fa fa-times-circle"></i></a></span> ';
}


function vmCreateDiskLabel(pk, name) {
  var style = "float: left; margin: 5px 5px 5px 0;";
  return '<span id="disk-' + pk + '" class="label label-primary" style="' + style + '"><i class="fa fa-file"></i> ' + name + ' <a href="#" class="hover-black vm-create-remove-disk"><i class="fa fa-times-circle"></i></a></span> ';
}
