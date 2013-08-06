$('#id_type').change(function() {
    type = $(":selected", this).text();
    resetForm();
    resetName();
});

$('#id_host').change(function() {
    var type = getType();
    host_id = $(":selected", this).val();
    host_name = $(":selected", this).text();

    // if user selected "----" reset the inputs
    if(!host_id) {
        resetForm();
    }
    // if A or AAAA record
    else if(type[0] === "A") {
        promise = getHostData(host_id);
        promise.success(function(data) {
            hostname = document.getElementById("id_name");
            hostname.disabled = true;
            hostname.value = data.hostname;
                    
            addr = document.getElementById("id_address")
            addr.disabled = true;
            if(type === "A") {
                addr.value = data.ipv4;
            } else {
                addr.value = data.ipv6;
            }
        });
    }
    // if CNAME
    else if(type === "CNAME") {
        resetForm();
        promise = getHostData(host_id);
        promise.success(function(data) {
            hostname = document.getElementById('id_name');
            hostname.disabled = true;
            hostname.value = data.hostname;
        });
    }
    // if MX
    else if(type === "MX") {
        resetForm();
        promise = getHostData(host_id);
        promise.success(function(data) {
            addr = document.getElementById('id_name');
            addr.value = "1D:" + data.fqdn;
        });

    }
});

// 
function getHostData(pk) {
    return $.ajax({                                                            
        type: "GET",                                                    
        url: "/network/hosts/" + pk + "/",                         
    });        
}

// return the currently selected type's name
function getType() {
    return $("#id_type :selected").text();
}

/*
 * reset the form
 *
 * enable hostname and address
 * and set the value to nothing
 *
 */
function resetForm() {
    hostname = document.getElementById('id_name');
    addr = document.getElementById('id_address');

    hostname.disabled = false;
    addr.disabled = false;

    hostname.value = "";
    addr.value = "";

}


// reset the hostname select
function resetName() {
    $("#id_host option").filter(function() {
        return $(this).text()[0] == "-"; 
    }).prop('selected', true);

}

/*
 * hides all of the inputs except the first
 *
 * this supposed to be a wizard thingy
 *
 */
$(function() {
    $('div[id^="div_id_"]').hide();
    $('#div_id_type .controls').append(
        ' <a id="type_next" onclick="type_next()" class="btn btn-info">Next</a>'
        );
    $('#div_id_type').fadeIn();
});

// if user clicked the "Next" button, this function will be called
function type_next() {
    $('#js_error').remove();
    if($('#div_id_type :selected').val()) {
        $('#type_next').remove();
        $('div[id^="div_id_"]').fadeIn();
    } else {
        appendMessage('error', 'type pls');
    }
    return false;
}


function appendMessage(type, message) {
    message = '<div id="js_error" style="display: none;" class="alert alert-' + type + '">' + message + '</div>';
    $('.form-horizontal').before(message);
    $('#js_error').fadeIn();
}
