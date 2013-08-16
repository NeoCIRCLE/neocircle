// regexes
mac_re = '^([0-9a-fA-F]{2}(:|$)){6}$';
alfanum_re = '^[A-Za-z0-9_-]+$';
domain_re = '^([A-Za-z0-9_-]\.?)+$';
ipv4_re = '^[0-9]+\.([0-9]+)\.([0-9]+)\.([0-9]+)$';
ipv6_re = '/^((?=.*::)(?!.*::.+::)(::)?([\dA-F]{1,4}:(:|\b)|){5}|([\dA-F]{1,4}:){6})((([\dA-F]{1,4}((?!\3)::|:\b|$))|(?!\2\3)){2}|(((2[0-4]|1\d|[1-9])?\d|25[0-5])\.?\b){4})$/i'
reverse_domain_re = '^(%\([abcd]\)d|[a-z0-9.-])+$';

var new_record = false;

$('#id_type').change(function() {
    type = $(":selected", this).text();
    resetForm();
    resetName();
    if(new_record) {
        type_next();
        new_record = false;
    }
});

$('#id_host').change(function() {    
    host_id = $("#id_host :selected").val();

    // if user selected "----" reset the inputs
    if(!host_id) {
        resetForm();
    } else {
        setNameAndAddress();
    }
});

function setNameAndAddress() {
    var type = $("#id_type :selected").text();
    host_id = $("#id_host :selected").val();
    host_name = $("#id_host :selected").text();

    // if A or AAAA record
    if(type[0] === "A") {
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
        promise = getHostData(host_id);
        promise.success(function(data) {
            addr = document.getElementById('id_address');
            addr.disabled = true;
            addr.value = data.fqdn;
        });
    }
    // if MX
    else if(type === "MX") {
        if(!$('#id_address').val()) {
            promise = getHostData(host_id);
            promise.success(function(data) {
                addr = document.getElementById('id_address');
                addr.value = "10:" + data.fqdn;
            });
        }

    }
}


$('#submit-id-submit').click(function() {
    return validateForm();
});

function validateForm() {
    type = $("#id_type :selected").text();
    host = $('#id_host :selected').val();

    messages = []
    // if host is set
    if(host && type[0] != "-") {
        if(type === "CNAME") {
            if(!$('#id_name').val()) {
                    messages.push({
                    'message': 'Name not set!',
                    'id': 'name'
                });
            }
        }
    // if host is not set
    } else if(!host && type[0] != "-") {
        if(!$('#id_address').val()) {
            messages.push({
                'message': 'No address set',
                'id': 'address'
            });
        } 
        // address is set
        else {
            var addr = $('#id_address').val();
            // ipv4
            if(type === "A") {
                if(!addr.match(ipv4_re)) {
                    messages.push({
                        'message': 'ipv4',
                        'id': 'address'
                    })
                }
            }
            // ipv6
            else if(type[0] === "A") {
                if(!addr.match(ipv6_re)) {
                    messages.push({
                        'message': 'ivp6',
                        'id': 'address'
                    });
                }
            }
            else if(type === "MX") {
                mx = addr.split(':');
                if(!(mx.length === 2 && mx[0].match("^[0-9]+$") && mx[1].match(domain_re))) {
                    messages.push({
                        'message': 'mx',
                        'id': 'address'
                    });
                }
            }
            else if(['CNAME', 'NS', 'PTR', 'TXT'].indexOf(type) != -1) {
                if(!addr.match(domain_re)) {
                    messages.push({
                        'message': 'address',
                        'id': 'address'
                    });
                }
            }
            else {
                messages.push({
                    'message': 'u wot m8'
                });
            }
        }
    } else {
        messages.push({
            'message': 'no type set',
            'id': 'type'
        });
    }

    // check other inputs
    
    // domain
    if(!$('#id_domain :selected').val()) {
        messages.push({
            'message': 'No domain set',
            'id': 'domain'
        });
    }
    // owner
    if(!$('#id_owner :selected').val()) {
        messages.push({
            'message': 'No owner set',
            'id': 'owner'
        });
    }

    if(messages.length < 1) {
        return true;
    } else {
        appendMessage('error', messages);
        return false;
    }
}

// 
function getHostData(pk) {
    return $.ajax({                                                            
        type: "GET",                                                    
        url: "/network/hosts/" + pk + "/",                         
    });        
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

    // reset invalid inputs too
    $('div[id^="div_id_"][class*="error"]').each(function() {
        $(this).removeClass('error');
    });

    // remove the error messages
    $("#js_error").fadeOut();

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
    // type is set, so it's an existing record
    if($('#id_type :selected').val()) {
        if($('#id_host :selected').val()) {
            setNameAndAddress();
        }
    }
    // else we are creaing a new
    else {
        new_record = true;
        // hide all input containers
        $('div[id^="div_id_"]').hide();
        // hide the save button
        $('#submit-id-submit').hide();
        $('#div_id_type .controls').append(
        //    ' <a id="type_next" onclick="type_next()" class="btn btn-info">Next</a>'
            '<span id="type_next" class="help-inline"><strong>Specify a type!</strong></span>'    
        );
        $('#div_id_type').fadeIn();
    }
});

// if user clicked the "Next" button, this function will be called
function type_next() {
    if($('#div_id_type :selected').val()) {
        $('#type_next').remove();
        $('div[id^="div_id_"]').fadeIn();
        $('#submit-id-submit').fadeIn();
    } else {
        message = [{
            'message': 'type pls',
            'id': 'type'
        }];
        appendMessage('error', message);
    }
    return false;
}

function appendMessage(type, messages, id) {
    $('#js_error').remove();
    message = '<div id="js_error" style="display: none;" class="alert alert-' + type + ' alert-block"><ul>'
    for(var i = 0;i < messages.length; i++) {
        message += "<li>" +messages[i].message+ "</li>";
        if(messages[i].id) {            
            $('#id_' + messages[i].id).closest('div[class="control-group"]').addClass("error");
        }
    }

    message +='</ul></div>';
    $('.form-horizontal').before(message);
    $('html, body').animate({ scrollTop: 0}, 'slow', function() {
        $('#js_error').fadeIn();   
    });
}

$('* [id^="id_"]').focus(function() {
    id = "#div_" + $(this).prop('id');
    if($(id).hasClass('error')) {
        $(id).removeClass('error');
    }
});
