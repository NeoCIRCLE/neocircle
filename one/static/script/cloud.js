var toggleDetails;
$(function() {
    toggleDetails = cloud.throttle(function() {
        if ($(this).parent('.entry').hasClass('opened')) {
            $(this).parent('.entry').removeClass('opened');
            $(this).next('.details').slideUp(700);
        } else {
            $(this).parent('.entry').addClass('opened');
            $(this).next('.details').slideDown(700);
        }
    })
    $('a[href=#]').click(function(e) {
        e.preventDefault();
    });
    $('.host-toggle').click(function(e){
        e.preventDefault();
        if($(this).find('.v4').is(':hidden')){
            $(this).find('.v4').show();
            $(this).find('.v6').hide();
            $(this).parent().next().find('.host').show();
            $(this).parent().next().find('.ipv4host').hide();
        } else {
            $(this).find('.v6').show();
            $(this).find('.v4').hide();
            $(this).parent().next().find('.host').hide();
            $(this).parent().next().find('.ipv4host').show();
        }
    });
    $('a[href!=#]').click(function(e) {
        e.stopPropagation();
    });
    $('.delete-template').click(function(e) {
        e.preventDefault();
        e.stopPropagation();
        delete_template_confirm($(this).data('url'), $(this).data('id'), $(this).data('name'));
    });
    $('.delete-key').click(function(e) {
        var id = $(this).data('id');
        e.preventDefault();
        e.stopPropagation();
        vm_confirm_popup(gettext('Are you sure deleting key?'), gettext('Delete'), function() {
            $.ajax({
                'type': 'POST',
                'data': 'id=' + id,
                'url': $(this).data('url'),
                'success': function() {
                    $('#key-' + id).slideUp(700);
                }
            });
        });
    });
    $('#reset-key').click(function(e) {
        vm_confirm_popup(gettext('Are you sure about reseting store credentials?<br /> You will lose your access to your store account on your existing virtual machines!'), gettext('Reset'), function() {
            $.ajax({
                type: 'POST',
                url: $(this).data('url'),
                success: function() {
                    window.location.reload();
                }
            })
        });
    });
    $('.entry .summary').click(toggleDetails);
    if (window.navigator.userAgent.indexOf('cloud-gui') < 0) {
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
        var handler = arguments.callee;
        var oldName = $(this).data('name');
        var content = $('#vm-' + id + '-name').html();
        var self=this;
        var url = $(this).data('url');
        $(this).unbind('click').click(function(e){
            e.preventDefault();
            e.stopPropagation();
            $(this).unbind('click').click(handler);
            $('#vm-' + id + '-name-details').show();
            $('#vm-' + id + '-name').html(content);
        })
        $('#vm-' + id + '-name-details').hide();
        $('#vm-' + id + '-name').html('<input type="text" value="' + oldName + '" />\
<input type="submit" value="' + gettext('Rename') + '" data-url="'+url+'"/>');
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
                url: $(this).data('url'),
                success: function(data) {
                    $('#vm-' + id + '-name-details').removeAttr('style');
                    $('#vm-' + id + '-name').text(data.name);
                    $(self).click(handler);
                }
            });
        })
    });
    $('.try-template').click(function(e) {
        e.preventDefault();
        e.stopPropagation();
        new_vm($(this).data('url'));
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
    $('.entry').on('click', '.renew-suspend-vm', function(e) {
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
        $.get($(this).data('url'), function(data) {
            $('#modal-container').html(data);
        })
        $('#modal').show();
    });
    $('.edit-template').click(function(e){
        e.preventDefault();
        e.stopPropagation();
        var id=$(this).data('id');
        $.ajax({
            type: 'GET',
            url: $(this).data('url'),
            success: function(data){
                $('#modal').show();
                $('#modal-container').html(data);
            }
        });
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
    $('.template-unshare').click(function(e) {
        e.stopPropagation();
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
        if (parseInt($(this).css('width')) > 0) $(this).css('borderRight', function(w) {
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
        });
        $('#modal .prev').click(function() {
            $('#modal').hide();
            $('#new-group-wizard').html(content);
        });

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
    $('.hidden-password').click(function() {
        if ($(this).attr('type') == 'password') {
            $(this).attr('type', 'text');
            $(this).addClass('shown');
            this.select();
        } else if (this.selectionStart - this.selectionEnd == 0) {
            $(this).attr('type', 'password');
            $(this).removeClass('shown');
        }
    });
    $('.shares li').click(function(e) {
        e.preventDefault();
        e.stopPropagation();
        e = $(this);
        if (!e.hasClass('description')) {
            if (e.next().is(':hidden')) {
                e.next().slideDown(700);
            } else {
                e.next().slideUp(700);
            }
        } else {
            e.slideUp(700);
        }
    });
    $('.shares .edit').click(function(e) {
        e.preventDefault();
        e.stopPropagation();
        $.ajax({
            type: 'GET',
            url: $(this).data('url'),
            success: function(data) {
                $('#modal').show();
                $('#modal-container').html(data);
            }
        })
    })
    $('.selected-summary').next().show();
    /**
     * Connect button new window
     */

    function get_vm_details(id) {
        $.get('/vm/credentials/' + id, function(data) {
            $('#modal-container').html(data);
            $('#modal-container .host-toggle').click(function(e){
                e.preventDefault();
                if($(this).find('.v4').is(':hidden')){
                    $(this).find('.v4').show();
                    $(this).find('.v6').hide();
                    $(this).parent().next().find('.host').show();
                    $(this).parent().next().find('.ipv4host').hide();
                } else {
                    $(this).find('.v6').show();
                    $(this).find('.v4').hide();
                    $(this).parent().next().find('.host').hide();
                    $(this).parent().next().find('.ipv4host').show();
                }
            });
            $('#modal-container .hidden-password').click(function() {
                if ($(this).attr('type') == 'password') {
                    $(this).attr('type', 'text');
                    $(this).addClass('shown');
                } else {
                    $(this).attr('type', 'password');
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

    cloud.confirm=vm_confirm_popup;
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
        manage_vm(id, "renew/suspend", function(data) {
            //workaround for some strange jquery parse error :o
            var foo=$('<div />').append(data);
            $('#vm-'+id+' .details-container').replaceWith(foo.find('.details-container'));
        });
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

    function manage_vm(id, state, f) {
        $.ajax({
            type: 'POST',
            url: '/vm/' + state + '/' + id + '/',
            success: function(data, b, c) {
                if(f) {
                    f(data);
                } else if (state == "resume") {
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

    function new_vm(url) {
        $.ajax({
            type: 'POST',
            url: url,
            success: function(data, b, xhrRequest) {
                window.location.href = xhrRequest.getResponseHeader("Location");
            }
        })
    }

    /**
     * Template delete
     */

    function delete_template_confirm(url, id, name) {
        confirm_message = interpolate(gettext("Are you sure deleting this %s template?"), ["<strong>" + name + "</strong>"])
        vm_confirm_popup(confirm_message, gettext("Delete"), function() {
            delete_template(url, id)
        })
    }
    /**
     * Template delete
     */

    function delete_template(url, id) {
        $.ajax({
            type: 'POST',
            url: url,
            data: 'id=' + id,
            dataType: 'json',
            statusCode: {
                404: function(data) {
                    alert(data['responseText']);
                },
                200: function(data) {
                    $("#t" + id).remove();
                    alert(gettext('Template deletion successful!'));
                },

            }
        })
    }

    function hide_group(id) {
        var hidden_groups = JSON.parse(window.localStorage.getItem('hidden_groups')) || {};
        var hidden_groups_for_user = hidden_groups[current_user] || [];
        for (var i in hidden_groups_for_user) {
            var hide = hidden_groups_for_user[i];
            if (hide == id) return false;
        }
        hidden_groups_for_user.push(id);
        hidden_groups[current_user] = hidden_groups_for_user;
        window.localStorage.setItem('hidden_groups', JSON.stringify(hidden_groups));
        $('#group-' + id).slideUp(700);
    }

    function hide_groups() {
        var hidden_groups = JSON.parse(window.localStorage.getItem('hidden_groups')) || {};
        var hidden_groups_for_user = hidden_groups[current_user] || [];
        for (var i in hidden_groups_for_user) {
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
        return (hidden_groups[current_user] || []).length;
    }

    function toggle_box(id) {
        var boxes = JSON.parse(window.localStorage.getItem('hidden_boxes')) || {};
        var user_boxes = boxes[current_user] || [];
        for (var i in user_boxes) {
            var box = user_boxes[i];
            if (box == id) {
                user_boxes.splice(i, 1);
                boxes[current_user] = user_boxes;
                window.localStorage.setItem('hidden_boxes', JSON.stringify(boxes));
                $('#toggle-box-' + id).attr('src', '/static/icons/eye-half.png');
                $('#toggle-box-' + id).parent().parent().parent().next().slideDown(700);
                return;
            }
        }
        user_boxes.push(id);
        boxes[current_user] = user_boxes;
        $('#toggle-box-' + id).attr('src', '/static/icons/eye.png');
        $('#toggle-box-' + id).parent().parent().parent().next().slideUp(700);
        console.log($('#toggle-box-' + id).parent().parent().parent().next()[0])
        window.localStorage.setItem('hidden_boxes', JSON.stringify(boxes));
    }

    function box_hidden(id) {
        var boxes = JSON.parse(window.localStorage.getItem('hidden_boxes')) || {};
        var user_boxes = boxes[current_user] || [];
        for (var i in user_boxes) {
            var box = user_boxes[i];
            if (box == id) {
                return true;
            }
        }
        return false;
    }

    $('.toggle-box').each(function() {
        var id = $(this).data('id');
        $(this).click(function() {
            toggle_box(id);
        });
        if (box_hidden(id)) {
            $(this).attr('src', '/static/icons/eye.png');
            $(this).parent().parent().parent().next().hide();
        } else {
            $(this).attr('src', '/static/icons/eye-half.png');
        }
    })

    if (hidden_group_count() == 0) {
        $('#show-hidden-groups').hide();
    }

    $('.hide-group').click(function(e) {
        e.preventDefault();
        e.stopPropagation();
        hide_group($(this).data('id'));
        if ($('#show-hidden-groups').is(':hidden')) {
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
            if ($(this).is(':hidden')) {
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
            url: $(this).data('url'),
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
        $('#new-owner-form input[type=text]').focus();
    });
    $('#new-owner-form input').click(function(e) {
        e.stopPropagation();
    });
    $('#new-owner-form input').keyup(function() {
        var timer;
        return function(e) {
            var val = $(this).val().split(' ')[0];
            var that = this;
            clearTimeout(timer);
            timer = setTimeout(function() {
                if (val.length < 1) return;
                $.ajax({
                    type: 'POST',
                    data: 'q=' + val,
                    url: $(that).data('url'),
                    dataType: 'json',
                    success: function(data) {
                        console.log(data);
                        $('#new-owner-autocomplete')[0].innerHTML = '<ul>';
                        var el = $('#new-owner-autocomplete')[0];
                        for (var i in data) {
                            var d = data[i];
                            el.innerHTML += '<li>' + d.name + ': ' + d.neptun + ' <input type="button" value="' + gettext('Add owner') + '" data-neptun="' + d.neptun + '" />' + '<div class="clear"></div></li>';
                        }
                        if (data.length == 0) {
                            el.innerHTML += '<li>' + gettext('Unknown') + ': ' + val + ' <input type="button" value="' + gettext('Add owner') + '" data-neptun="' + val + '" />' + '<div class="clear"></div></li>';
                        }
                        el.innerHTML += '</ul>';
                        $(el).find('input').each(function() {
                            var self = this;
                            $(this).click(function(e) {
                                e.stopPropagation();
                                $.ajax({
                                    type: 'POST',
                                    data: 'neptun=' + $(self).data('neptun'),
                                    url: '/ajax/group/' + $('#new-owner').data('gid') + '/addOwner/',
                                    dataType: 'json',
                                    success: function(data) {
                                        window.location.reload();
                                    }
                                })
                            })
                        })
                    }
                });
            }, 1000);
            e.stopPropagation();
        }
    }());

    $('#group-members .remove').click(function(e) {
        e.preventDefault();
        e.stopPropagation();
        var neptun = $(this).data('neptun');
        $.ajax({
            type: 'POST',
            url: $(this).data('url'),
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
        var url = $(this).data('url');
        vm_confirm_popup(
        interpolate(
        gettext('Are you sure deleting <strong>%s</strong>'), [name]), gettext('Delete'), function() {
            $.ajax({
                type: 'POST',
                url: url,
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
