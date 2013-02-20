var toggleDetails;
$(function() {
    toggleDetails = cloud.throttle(function() {
        if($(this).parent('.entry').hasClass('opened')) {
            $(this).parent('.entry').removeClass('opened');
            $(this).next('.details').slideUp(700);
        } else {
            $(this).parent('.entry').addClass('opened');
            $(this).next('.details').slideDown(700);
        }
    })
    $('.delete-template-button').click(function(e) {
        e.preventDefault();
        e.stopPropagation();
        delete_template_confirm($(this).data('id'), $(this).data('name'));
    });
    $('.delete-key-button').click(function(e) {
        var id = $(this).data('id');
        e.preventDefault();
        e.stopPropagation();
        vm_confirm_popup(gettext('Are you sure deleting key?'), gettext('Delete'), function() {
            $.ajax({
                'type': 'POST',
                'data': 'id=' + id,
                'url': '/ajax/key/delete/',
                'success': function() {
                    $('#key-' + id).slideUp(700);
                }
            });
        });
    });
    $('.entry .summary').unbind('click').click(toggleDetails);
    if(window.navigator.userAgent.indexOf('cloud-gui') > -1) {
        $('.connect-vm').click(function(e) {
            e.preventDefault();
            e.stopPropagation();
            get_vm_details($(this).data('id'));
        });
    } else {
        $('.connect-vm').click(function(e) {
            e.stopPropagation();
        });
    }
    $('.rename-vm').click(function(e) {
        e.preventDefault();
        e.stopPropagation();
        var id = $(this).data('id');
        var oldName = $(this).data('name');
        $('#vm-' + id + '-name-details').hide();
        $('#vm-' + id + '-name').html('<input type="text" value="' + oldName + '" />\
<input type="submit" value="' + gettext('Rename') + '" />');
        $('#vm-' + id + '-name').find('input[type="text"]').click(function(f) {
            f.preventDefault();
            f.stopPropagation();
        }).focus();
        $('#vm-' + id + '-name').find('input[type=submit]').click(function(f) {
            f.preventDefault();
            f.stopPropagation();
            var newName = $(this).prev().val();
            $.ajax({
                type: 'POST',
                data: 'name=' + newName,
                dataType: 'json',
                url: '/ajax/vm/rename/' + id + '/',
                success: function(data) {
                    $('#vm-' + id + '-name-details').removeAttr('style');
                    $('#vm-' + id + '-name').text(data.name);
                }
            });
        })
    });
    $('.try-template-button').click(function(e) {
        e.preventDefault();
        e.stopPropagation();
        new_vm($(this).data('id'));
    });
    $('.stop-vm').click(function(e) {
        e.preventDefault();
        e.stopPropagation();
        stop_vm($(this).data('id'), $(this).data('name'));
    });
    $('.resume-vm').click(function(e) {
        e.preventDefault();
        e.stopPropagation();
        manage_vm($(this).data('id'), "resume");
    });
    $('.delete-vm').click(function(e) {
        e.preventDefault();
        e.stopPropagation();
        delete_vm($(this).data('id'), $(this).data('name'));
    });
    $('.restart-vm').click(function(e) {
        e.preventDefault();
        e.stopPropagation();
        restart_vm($(this).data('id'), $(this).data('name'));
    });
    $('.renew-suspend-vm').click(function(e) {
        e.preventDefault();
        e.stopPropagation();
        renew_suspend_vm($(this).data('id'))
    });
    $('.renew-delete-vm').click(function(e) {
        e.preventDefault();
        e.stopPropagation();
        renew_delete_vm($(this).data('id'))
    });
    $('#new-vm-button').click(function() {
        $('#modal').show();
        $('#modal-container').html($('#new-vm').html());
        $('#modal-container .entry .summary').click(toggleDetails);
    });
    $('#new-template-button').click(function() {
        $.get('/ajax/templateWizard', function(data) {
            $('#modal-container').html(data);
        })
        $('#modal').show();
    });
    $('#shadow').click(function() {
        $('#modal').hide();
        $('#modal-container').html('');
    })
    $('.template-share').click(function(e) {
        e.preventDefault();
        e.stopPropagation();
        $.get('/ajax/share/' + $(this).data('id') + '/' + $(this).data('gid'), function(data) {
            $('#modal-container').html(data);
        })
        $('#modal').show();
    });
    $('#old-upload').click(function(e) {
        e.preventDefault();
        $(this).parent().parent().hide().parent().find('#old-upload-form').show();
        return false;
    });
    $('.quota .used').each(function() {
        var s = this;
        $(this).css('backgroundColor', function(w) {
            return 'hsla(' + (120 - parseFloat(w) / 100 * 120).toFixed(0) + ', 100%, 50%, 0.2)';
        }($(this)[0].style.width));
        if(parseInt($(this).css('width')) > 0) $(this).css('borderRight', function(w) {
            return '1px solid hsla(' + (120 - parseFloat(w) / 100 * 120).toFixed(0) + ', 100%, 30%, 0.4)';
        }($(this)[0].style.width));
    });
    $('#new-folder').click(function() {
        $('#new-folder-form input')[0].focus();
    });
    $('#new-group').click(function() {
        var content = $('#new-group-wizard').html();
        $('#new-group-wizard').html('');
        $('#modal').show();
        $('#modal-container').html(content);
        $('#shadow').click(function() {
            $('#new-group-wizard').html(content);
        })

        function updateSummary() {
            $('#new-group-summary-name').html($('#new-group-name').val());
            $('#new-group-summary-count').html(function(text) {
                var m = text.match(/\s*[a-z][0-9a-z]{5}\s*(\r|\n|$)+/gi);
                return m ? m.length : 0;
            }($('#new-group-members').val()));
            $('#new-group-summary-semester').html($('#new-group-semester')[0].options[$('#new-group-semester')[0].selectedIndex].innerHTML)
        }
        $('#new-group-name').change(updateSummary);
        $('#new-group-semester').change(updateSummary);
        $('#new-group-members').change(updateSummary);
    });
    $('#vm-password-show').click(function() {
        $('#vm-password-show').hide();
        $('#vm-password').show();
    });
    $('.hidden-password').each(function() {
        $(this).val('******');
    });
    $('.hidden-password').click(function() {
        if(!$(this).hasClass('shown')) {
            $(this).val($(this).data('value'));
            $(this).addClass('shown');
        } else {
            $(this).val('******');
            $(this).removeClass('shown');
        }
    })
    toggleDetails.apply($('.selected-summary'));
    toggleDetails.apply($('.selected-summary'));
    /**
     * Connect button new window
     */

    function get_vm_details(id) {
        $.get('/vm/credentials/' + id, function(data) {
            $('#modal-container').html(data);
            $('.hidden-password').each(function() {
                $(this).val('******');
            });
            $('.hidden-password').click(function() {
                if(!$(this).hasClass('shown')) {
                    $(this).val($(this).data('value'));
                    $(this).addClass('shown');
                } else {
                    $(this).val('******');
                    $(this).removeClass('shown');
                }
            })
        })
        $('#modal').show();
    };
    /**
     * Confirm pop-up window
     */

    function vm_confirm_popup(confirm_message, button_text, success) {
        $('#modal').show();
        $('#modal-container').html(confirm_message + '<br /><input class="ok" type="button" value="' + button_text + '" style="float: left"/><input class="cancel" type="button" value="' + gettext('Cancel') + '" style="float: right" />');
        $('#modal-container .ok').click(function() {
            $('#modal').hide();
            success();
        });
        $('#modal-container .cancel').click(function() {
            $('#modal').hide();
        });
    }
    /**
     * Manage VM State (STOP)
     */

    function stop_vm(id, name) {
        confirm_message = interpolate(gettext("Are you sure stopping %s?"), ["<strong>" + name + "</strong>"])
        vm_confirm_popup(confirm_message, gettext("Stop"), function() {
            manage_vm(id, "stop")
        });
    }
    /**
     * Manage VM State (DELETE)
     */

    function delete_vm(id, name) {
        confirm_message = interpolate(gettext("Are you sure deleting %s?"), ["<strong>" + name + "</strong>"])
        vm_confirm_popup(confirm_message, gettext("Delete"), function() {
            manage_vm(id, "delete")
        })
    }
    /**
     * Manage VM State (RESET)
     */

    function restart_vm(id, name) {
        confirm_message = interpolate(gettext("Are you sure restarting %s?"), ["<strong>" + name + "</strong>"])
        vm_confirm_popup(confirm_message, gettext("Restart"), function() {
            manage_vm(id, "restart")
        })
    }
    /**
     * Manage VM State (RESUME)
     */

    function resume_vm(id, name) {
        manage_vm(id, "resume")
    }
    /**
     * Renew vm suspend time.
     */

    function renew_suspend_vm(id) {
        manage_vm(id, "renew/suspend")
    }
    /**
     * Renew vm deletion time.
     */

    function renew_delete_vm(id) {
        manage_vm(id, "renew/delete")
    }
    /**
     * Manage VM State generic
     */

    function manage_vm(id, state) {
        $.ajax({
            type: 'POST',
            url: '/vm/' + state + '/' + id + '/',
            success: function(data, b, c) {
                if(state == "resume") {
                    window.location.href = '/vm/show/' + id + "/";
                } else {
                    window.location.reload();
                }
            }
        })
    }
    /**
     * New VM
     */

    function new_vm(template_id) {
        $.ajax({
            type: 'POST',
            url: '/ajax/vm/new/' + template_id + '/',
            success: function(data, b, xhrRequest) {
                window.location.href = '/'; //xhrRequest.getResponseHeader("Location");
                //alert(xhrRequest.getResponseHeader("Location"));
                window.location.href = xhrRequest.getResponseHeader("Location");
            }
        })
    }

    /**
     * Template delete
     */

    function delete_template_confirm(id, name) {
        confirm_message = interpolate(gettext("Are you sure deleting this %s template?"), ["<strong>" + name + "</strong>"])
        vm_confirm_popup(confirm_message, gettext("Delete"), function() {
            delete_template(id)
        })
    }
    /**
     * Template delete
     */

    function delete_template(id) {
        $.ajax({
            type: 'POST',
            url: '/ajax/template/delete/',
            data: 'id=' + id,
            dataType: 'json',
            statusCode: {
                404: function(data) {
                    alert(data['responseText']);
                },
                200: function(data) {
                    $("#t" + id).remove()
                },

            }
        })
    }

    function hide_group(id) {
        var hidden_groups = JSON.parse(window.localStorage.getItem('hidden_groups')) || {};
        var hidden_groups_for_user = hidden_groups[current_user] || [];
        for(var i in hidden_groups_for_user) {
            var hide = hidden_groups_for_user[i];
            if(hide == id) return false;
        }
        hidden_groups_for_user.push(id);
        hidden_groups[current_user] = hidden_groups_for_user;
        window.localStorage.setItem('hidden_groups', JSON.stringify(hidden_groups));
        $('#group-' + id).slideUp(700);
    }

    function hide_groups() {
        var hidden_groups = JSON.parse(window.localStorage.getItem('hidden_groups')) || {};
        var hidden_groups_for_user = hidden_groups[current_user] || [];
        for(var i in hidden_groups_for_user) {
            var hide = hidden_groups_for_user[i];
            $('#group-' + hide).hide();
        }
    }

    function show_hidden_groups() {
        var hidden_groups = JSON.parse(window.localStorage.getItem('hidden_groups')) || {};
        hidden_groups[current_user] = [];
        window.localStorage.setItem('hidden_groups', JSON.stringify(hidden_groups));
    }
    hide_groups();

    function hidden_group_count() {
        var hidden_groups = JSON.parse(window.localStorage.getItem('hidden_groups')) || {};
        return(hidden_groups[current_user] || []).length;
    }
    if(hidden_group_count() == 0) {
        $('#show-hidden-groups').hide();
    }

    $('.hide-group').click(function(e) {
        e.preventDefault();
        e.stopPropagation();
        hide_group($(this).data('id'));
        if($('#show-hidden-groups').is(':hidden')) {
            $('#show-hidden-groups').slideDown(700);
        }
        return false;
    });
    $('#show-hidden-groups').click(function(e) {
        e.preventDefault();
        e.stopPropagation();
        show_hidden_groups();
        $('#show-hidden-groups').slideUp(700);
        $('#groups > li').each(function() {
            if($(this).is(':hidden')) {
                $(this).slideDown(700);
            }
        })
    })
    $('#new-member').click(function() {
        $('#new-member-form').toggle();
    });
    $('#new-member-form input').click(function(e) {
        e.stopPropagation();
    });
    $('#new-member-form input[type=submit]').click(function() {
        var neptun = $(this).prev().val();
        $.ajax({
            type: 'POST',
            url: '/ajax/group/' + $(this).data('id') + '/add/',
            data: 'neptun=' + neptun,
            dataType: 'json',
            success: function(data) {
                window.location.reload();
            }
        }).error(function(data) {
            //TODO: fancy modal alert
            alert(JSON.parse(data.responseText).status);
        })
    });

    $('#new-owner').click(function() {
        $('#new-owner-form').toggle();
    });
    $('#new-owner-form input').click(function(e) {
        e.stopPropagation();
    });
    $('#new-owner-form input[type=submit]').click(function() {
        var neptun = $(this).prev().val();
        $.ajax({
            type: 'POST',
            url: '/ajax/group/' + $(this).data('id') + '/add/',
            data: 'neptun=' + neptun,
            dataType: 'json',
            success: function(data) {
                window.location.reload();
            }
        }).error(function(data) {
            //TODO: fancy modal alert
            alert(JSON.parse(data.responseText).status);
        })
    });

    $('#group-members .remove').click(function(e) {
        e.preventDefault();
        e.stopPropagation();
        var neptun = $(this).data('neptun');
        $.ajax({
            type: 'POST',
            url: '/ajax/group/' + $(this).data('gid') + '/remove/',
            data: 'neptun=' + neptun,
            success: function(data) {
                $('#member-' + neptun).slideUp(700);
            }
        });
    });
    $('#groups .delete').click(function(e) {
        e.preventDefault();
        e.stopPropagation();
        var gid = $(this).data('id');
        var name = $(this).data('name');
        vm_confirm_popup(
        interpolate(
        gettext('Are you sure deleting <strong>%s</strong>'), [name]), gettext('Delete'), function() {
            $.ajax({
                type: 'POST',
                url: '/ajax/group/delete/',
                data: 'gid=' + gid,
                success: function() {
                    $('#group-' + gid).slideUp(700);
                }
            }).error(function() {
                window.location.reload();
            })
        })
    })
})
