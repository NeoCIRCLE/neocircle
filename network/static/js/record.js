// regexes
mac_re = /^([0-9a-fA-F]{2}(:|$)){6}$/;
alfanum_re = '^[A-Za-z0-9_-]+$';
domain_re = /^([A-Za-z0-9_-]\.?)+$/;
ipv4_re = /^[0-9]+\.([0-9]+)\.([0-9]+)\.([0-9]+)$/;
ipv6_re = /^((?=.*::)(?!.*::.+::)(::)?([\dA-F]{1,4}:(:|\b)|){5}|([\dA-F]{1,4}:){6})((([\dA-F]{1,4}((?!\3)::|:\b|$))|(?!\2\3)){2}|(((2[0-4]|1\d|[1-9])?\d|25[0-5])\.?\b){4})$/i
reverse_domain_re = /^(%\([abcd]\)d|[a-z0-9.-])+$/;

// is this a new record?
var new_record = false;

// handles type change
// if we are currently creating a new one, call type_next()
$('#id_type').change(function() {
    type = $(":selected", this).text();
    resetForm();
    resetName();
    if(new_record) {
        type_next();
        new_record = false;
    }
});


// handles hostname change
$('#id_host').change(function() {    
    host_id = $("#id_host :selected").val();

    // if user selected "----" reset the inputs
    if(!host_id) {
        resetForm();
    } else {
        setNameAndAddress();
        resetErrors();
    }
});

// sets the name and address if necessary
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

// if we submit the form validate the form
$('#submit-id-submit').click(function() {
    return validateForm();
});

// validates the form
// validation is like the one in firewall/model.py
function validateForm() {
    type = $("#id_type :selected").text();
    host = $('#id_host :selected').val();

    messages = []
    // if host is set
    if(host && type[0] != "-") {
        if(type === "CNAME") {
            if(!$('#id_name').val()) {
                    messages.push({
                    'message': 'Name must be specified for ' +
                               'CNAME records if host is set!',
                    'id': 'name'
                });
            }
        }
    // if host is not set
    } else if(!host && type[0] != "-") {
        if(!$('#id_address').val()) {
            messages.push({
                'message': gettext('Address must be specified!'),
                'id': 'address'
            });
        } 
        // address is set
        else {
            var addr = $('#id_address').val();
            // ipv4
            if(type === "A") {
                if(!addr.match(ipv4_re)) {
                    text = gettext('%s - not an IPv4 address');
                    messages.push({
                        'message': interpolate(text, [addr]),
                        'id': 'address'
                    })
                }
            }
            // ipv6
            else if(type[0] === "A") {
                if(!addr.match(ipv6_re)) {
                    text = gettext('%s - not an IPv6 address');
                    messages.push({
                        'message': interpolate(text, [addr]),
                        'id': 'address'
                    });
                }
            }
            // MX
            else if(type === "MX") {
                mx = addr.split(':');
                if(!(mx.length === 2 && mx[0].match("^[0-9]+$") && domain_re.test(mx[1]))) {
                    text = gettext('Bad MX address format. ' + 
                                   'Should be: <priority>:<hostname>')
                    messages.push({
                        'message': text,
                        'id': 'address'
                    });
                }
            }
            // CNAME / NS / PTR / TXT
            else if(['CNAME', 'NS', 'PTR', 'TXT'].indexOf(type) != -1) {
                if(!domain_re.test(addr)) {
                    text = gettext('%s - invalid domain name');
                    messages.push({
                        'message': interpolate(text, [addr]),
                        'id': 'address'
                    });
                }
            }
            // we doesn't really need this, but better safe than sorry
            else {
                messages.push({
                    'message': gettext('Unknown record type.'),
                    'id': 'type'
                });
            }
        }
    // we didn't choose a type
    } else {
        messages.push({
            'message': gettext('You must choose a type'),
            'id': 'type'
        });
    }

    // check other inputs
    
    // name
    record_name = $('#id_name').val()
    
    if(!record_name) {
        //messages.push({ 
        //    'message': gettext("You must specify a name!"),
        //    'id': 'name'
        //});
    }
    else if(!domain_re.test(record_name)) {
        text = gettext('%s - invalid domain name'),
        messages.push({
            'message': interpolate(text, [record_name]),
            'id': 'name'
        });
    }

    // domain
    if(!$('#id_domain :selected').val()) {
        messages.push({
            'message': gettext('You must choose a domain'),
            'id': 'domain'
        });
    }
    // owner
    if(!$('#id_owner :selected').val()) {
        messages.push({
            'message': gettext('You must specify an owner!'),
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

// makes the ajax call
function getHostData(pk) {
    return $.ajax({                                                            
        type: "GET",                                                    
        url: "/network/hosts/" + pk + "/",                         
    });        
}

// enables fields, resets them and removes error messages
function resetForm() {
    hostname = document.getElementById('id_name');
    addr = document.getElementById('id_address');

    hostname.disabled = false;
    addr.disabled = false;

    hostname.value = "";
    addr.value = "";

    resetErrors();
}

// removes all error messages / classes
function resetErrors() {
    // reset invalid inputs too
    $('div[id^="div_id_"][class*="has-error"]').each(function() {
        $(this).removeClass('has-error');
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


// on page load
// if we are upadting
//      - set the name and address
// else it's a new rule so we "create" the wizard thingy
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
        // 
        $('#div_id_type .controls')
        .addClass('input-group')
        .append(
            //' <a id="type_next" onclick="type_next()" class="btn btn-info">Next</a>'
            '<span id="type_next" class="input-group-addon"><strong>' + 
            gettext('Specify a type!') + 
            '</strong></span>'    
        );
        $('#div_id_type').fadeIn();
    }
});

// if the user choose a type 
function type_next() {
    if($('#div_id_type :selected').val()) {
        $('#div_id_type .controls').removeClass('input-group');
        $('#type_next').remove();
        $('div[id^="div_id_"]').fadeIn();
        $('#submit-id-submit').fadeIn();
    // this shouldn't be called ...
    } else {
        message = [{
            'message': gettext('You must choose a type'),
            'id': 'type'
    }];
        appendMessage('error', message);
    }
    return false;
}

/*
 * error creating function
 *
 * first it removes the current error message, then it iterates through
 * all the given messages
 */
function appendMessage(type, messages, id) {
    $('#js_error').remove();
    resetErrors();
    message = '<div id="js_error" style="display: none;" class="alert alert-danger"><ul>'
    for(var i = 0;i < messages.length; i++) {
        message += "<li>" +messages[i].message+ "</li>";
        if(messages[i].id) {            
            $('#id_' + messages[i].id).closest('div[class="form-group"]').addClass("has-error");
        }
    }

    message +='</ul></div>';
    $('form').before(message);
    $('html, body').animate({ scrollTop: 0}, 'slow', function() {
        $('#js_error').fadeIn();   
    });
}


// remove error class from forms if we click on them
// it also removes the help-inline span that shouldn't really appear
$('* [id^="id_"]').focus(function() {
    id = "#div_" + $(this).prop('id');
    if($(id).hasClass('has-error')) {
        $(id).removeClass('has-error');
        $('span[id="error_1_' + $(this).attr('id') + '"]').remove();
    }
});
