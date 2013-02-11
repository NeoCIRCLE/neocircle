var toggleDetails;
$(function() {
    function getCookie(name) {
        var cookieValue = null;
        if(document.cookie && document.cookie != '') {
            var cookies = document.cookie.split(';');
            for(var i = 0; i < cookies.length; i++) {
                var cookie = jQuery.trim(cookies[i]);
                if(cookie.substring(0, name.length + 1) == (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    var csrftoken = getCookie('csrftoken');

    function csrfSafeMethod(method) {
        return(/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
    }
    $.ajaxSetup({
        crossDomain: false,
        beforeSend: function(xhr, settings) {
            if(!csrfSafeMethod(settings.type)) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            }
        }
    });
    toggleDetails = function() {
        if($(this).parent('.wm').hasClass('opened')) {
            $(this).parent('.wm').removeClass('opened');
            $(this).next('.details').slideUp(700);
        } else {
            $(this).parent('.wm').addClass('opened');
            $(this).next('.details').slideDown(700);
        }
    }
    $('.delete-template-button').click(function(e) {
        e.preventDefault(); e.stopPropagation();
        delete_template_confirm($(this).data('id'), $(this).data('name'));
    });
    $('.wm .summary').unbind('click').click(toggleDetails);
    if (window.navigator.userAgent.indexOf('cloud-gui') != 0) {
        $('.connect-vm-button').click(function(e) {
            e.preventDefault(); e.stopPropagation();
            get_vm_details($(this).data('id'));
        });
    }
    else {
        $('.connect-vm-button').click(function(e) {
            e.stopPropagation();
        });
    }
    $('.try-template-button').click(function(e) {
        e.preventDefault(); e.stopPropagation();
        new_vm($(this).data('id') );
    });
    $('.stop-vm-button').click(function(e) {
        e.preventDefault(); e.stopPropagation();
        stop_vm($(this).data('id'), $(this).data('name'));
    });
    $('.resume-vm-button').click(function(e) {
        e.preventDefault(); e.stopPropagation();
        manage_vm($(this).data('id'), "resume");
    });
    $('.delete-vm-button').click(function(e) {
        e.preventDefault(); e.stopPropagation();
        delete_vm($(this).data('id'), $(this).data('name'));
    });
    $('.restart-vm-button').click(function(e) {
        e.preventDefault(); e.stopPropagation();
        restart_vm($(this).data('id'), $(this).data('name'));
    });
    $('#new-wm-button').click(function() {
        $('#modal').show();
        $('#modal-container').html($('#new-wm').html());
        $('#modal-container .wm .summary').click(toggleDetails);
    });
    /*
     *FIXME Most ez itt miért van 2x??????
     */
    $('#new-template-button').click(function() {
        $('#modal').show();
        $('#modal-container').html($('#new-template').html());
    });
    $('#new-template-button').click(function() {
        $.get('/ajax/templateWizard', function(data) {
            $('#modal-container').html(data);
        })
        $('#modal').show();
    });
    $('#shadow').click(function() {
        $('#modal').hide();
    })
    $('.template-share').click(function(e) {
        e.preventDefault(); e.stopPropagation();
        $.get('/ajax/share/'+$(this).data('id'), function(data) {
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
            return 'hsla(' + (120 - parseFloat(w) / 100 * 120).toFixed(0) + ',100%,50%,0.2)';
        }($(this)[0].style.width));
        if(parseInt($(this).css('width')) > 0) $(this).css('borderRight', function(w) {
            return '1px solid hsla(' + (120 - parseFloat(w) / 100 * 120).toFixed(0) + ',100%,30%,0.4)';
        }($(this)[0].style.width));
    });
    $('#new-folder').click(function() {
        $('#new-folder-form input')[0].focus();
    });
    $('#new-group').click(function() {
        var content = $('#new-group-wizard').html();
//        $('#new-group-wizard').parent()[0].removeChild($('#new-group-wizard')[0]);
        $('#modal').show();
        $('#modal-container').html(content);

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
    toggleDetails.apply($('.selected-summary'));
    toggleDetails.apply($('.selected-summary'));
    /**
     * Connect button new window
     */
    function get_vm_details(id) {
        $.get('/vm/credentials/'+id, function(data) {
            $('#modal-container').html(data);
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
        confirm_message = interpolate(gettext("Are you sure stopping %s?"), ["<strong>"+name+"</strong>"])
        vm_confirm_popup(confirm_message, gettext("Stop"), function() {
            manage_vm(id, "stop")
        });
    }
    /**
     * Manage VM State (DELETE)
     */

    function delete_vm(id, name) {
        confirm_message = interpolate(gettext("Are you sure deleting %s?"), ["<strong>"+name+"</strong>"])
        vm_confirm_popup(confirm_message, gettext("Delete"), function() {
            manage_vm(id, "delete")
        })
    }
    /**
     * Manage VM State (RESET)
     */

    function restart_vm(id, name) {
        confirm_message = interpolate(gettext("Are you sure restarting %s?"), ["<strong>"+name+"</strong>"])
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
     * Manage VM State generic
     */

    function manage_vm(id, state) {
        $.ajax({
            type: 'POST',
            url: '/vm/' + state + '/' + id + '/',
            success: function(data, b, c) {
                if ( state == "resume"){
                    window.location.href = '/vm/show/'+id+"/";
                }
                else {
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
            url: 'ajax/vm/new/' + template_id + '/',
            success: function(data, b, xhrRequest) {
                window.location.href = xhrRequest.getResponseHeader("Location");
                //alert(xhrRequest.getResponseHeader("Location"));
            }
        })
    }

    /**
     * Template delete
     */
    function delete_template_confirm(id, name) {
        confirm_message = interpolate(gettext("Are you sure deleting this %s template?"), ["<strong>"+name+"</strong>"])
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
                $("#t"+id).remove()
            },

            }
        })
    }

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
    $('#group-members .remove').click(function(e) {
        e.preventDefault();
        e.stopPropagation();
        $.ajax({
            type: 'POST',
            url: '/ajax/group/' + $(this).data('gid') + '/remove/',
            data: 'neptun=' + $(this).data('neptun'),
            success: function(data) {
                window.location.reload();
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
                    window.location.reload();
                }
            }).error(function() {
                window.location.reload();
            })
        })
    })

    /**
     * Convert bytes to human readable format
     */

    function convert(n, skip, precision) {
        skip = skip | 0;
        precision = precision | 2;
        var suffix = 'B KB MB GB'.split(' ');
        for(var i = skip; n > 1024; i++) {
            n /= 1024;
        }
        return n.toFixed(precision) + ' ' + suffix[i];
    }

    function Model() {
        //alias for this
        var self = this;
        var uploadURLRequestInProgress = false;
        //currently displayed files
        self.files = ko.observableArray();
        //false, if you are in /
        self.notInRoot = ko.observable(false);
        //defalut path to display
        self.currentPath = ko.observable('/');
        //default upload url (invalid)
        self.uploadURL = ko.observable('/');
        self.newFolderName = ko.observable();
        self.uploadProgress = ko.observable('0%');
        self.quota = {
            rawUsed: ko.observable(0),
            rawSoft: ko.observable(0),
            rawHard: ko.observable(0)
        };
        self.quota.used = ko.computed(function() {
            return convert(self.quota.rawUsed(), 1);
        });
        self.quota.hard = ko.computed(function() {
            return convert(self.quota.rawHard(), 1);
        });
        self.quota.soft = ko.computed(function() {
            return convert(self.quota.rawSoft(), 1);
        });
        self.quota.usedBar = ko.computed(function() {
            return(self.quota.rawUsed() / self.quota.rawHard() * 100).toFixed(0) + '%';
        }, self);
        self.quota.softPos = ko.computed(function() {
            return(self.quota.rawSoft() / self.quota.rawHard() * 100).toFixed(0) + '%';
        }, self);
        self.sortBy = ko.observable('name');

        $('#current-location select').on('change', function() {
            self.sortBy($('#current-location select').val());
            sortFiles();
        })

        /**
         * Returns throttled function
         */

        function throttle(f) {
            var disabled = false;
            return function() {
                if(disabled) {
                    return
                };
                disabled = true;
                setTimeout(function() {
                    disabled = false;
                }, 700);
                f.apply(null, arguments);
            }
        }

        /**
         * Delay the function call for `f` until `g` evaluates true
         * Default check interval is 1 sec
         */

        function delayUntil(f, g, timeout) {
            var timeout = timeout | 1000;

            function check() {
                var o = arguments;
                if(!g()) {
                    setTimeout(function() {
                        check.apply(null, o)
                    }, timeout);
                    return;
                }
                f.apply(null, o);
            }
            return function() {
                check.apply(null, arguments);
            }
        }

        /**
         * Loads the parent folder
         */
        self.jumpUp = function() {
            var s = self.currentPath();
            loadFolder(s.substr(0, s.substr(0, s.length - 1).lastIndexOf('/') + 1));
        }

        var sortFiles = function() {
                self.files.sort({
                    name: function(a, b) {
                        if(a.type === b.type) {
                            return a.originalName.localeCompare(b.originalName);
                        }
                        if(a.type === gettext('file')) {
                            return 1;
                        }
                        return -1;
                    },
                    date: function(a, b) {
                        if(a.type === b.type) {
                            return new Date(b.mTime).getTime() - new Date(a.mTime).getTime();
                        }
                        if(a.type === gettext('file')) {
                            return 1;
                        }
                        return -1;
                    },
                    size: function(a, b) {
                        if(a.type === b.type) {
                            return b.originalSize - a.originalSize;
                        }
                        if(a.type === gettext('file')) {
                            return 1;
                        }
                        return -1;
                    },
                }[self.sortBy()]);
            }

            /**
             * Loads the specified folder
             */
        var loadFolder = throttle(function(path, fast) {
            self.currentPath(path);
            self.fileLimit = 5;
            $.ajax({
                type: 'POST',
                data: 'path=' + path,
                url: '/ajax/store/list',
                dataType: 'json',
                success: function(data) {
                    if(!fast) {
                        $('.file-list .real').css({
                            left: 0,
                            position: 'relative'
                        }).animate({
                            left: '-100%'
                        }, 500).promise().done(function() {
                            loadFolderDone(data);
                            $('.file-list .real').css({
                                left: '-300%',
                                position: 'relative'
                            }).animate({
                                left: 0
                            }, 500);
                        });
                    } else {
                        loadFolderDone(data);
                    }
                },
            })
        })

        /**
         * After loadFolder completes, this function updates the UI
         */

        function loadFolderDone(data) {
            var viewData = [];
            var added = 0;
            self.notInRoot(self.currentPath().lastIndexOf('/') !== 0);
            self.files([]);
            for(var i in data) {
                addFile(data[i]);
            }
            sortFiles();
        }

        /**
         * Add file to the displayed files list
         */

        function addFile(d) {
            var viewData;
            if(d.TYPE === 'D') {
                viewData = {
                    originalName: d.NAME,
                    originalSize: 0,
                    name: d.NAME.length > 30 ? (d.NAME.substr(0, 27) + '...') : d.NAME,
                    size: 'katalógus',
                    type: 'katalógus',
                    mTime: d.MTIME,
                    getTypeClass: 'name filetype-folder',
                    clickHandler: function(item) {
                        loadFolder(self.currentPath() + item.originalName + '/');
                    }
                };
            } else {
                var type = 'text';
                var ext = {
                    image: /\.(jpg|png|gif|jpeg)$/,
                    pdf: /\.pdf$/,
                    doc: /\.docx?$/,
                    excel: /\.xlsx?$/,
                    csv: /\.csv$/,
                    php: /\.php$/,
                    tex: /\.tex$/,
                    ppt: /\.pptx?/,
                    music: /\.(wav|mp3)$/
                };
                for(var i in ext) {
                    if(d.NAME.match(ext[i])) {
                        type = i;
                        break;
                    }
                }
                var extension;
                try {
                    extension=d.NAME.match(/\.\w+$/)[0].substr(1);
                }
                catch (ex) {
                    extension='N/A';
                }
                viewData = {
                    originalName: d.NAME,
                    originalSize: d.SIZE,
                    name: d.NAME.length > 30 ? (d.NAME.substr(0, 20) + '... ('+extension+')') : d.NAME,
                    size: convert(d.SIZE),
                    type: gettext('file'),
                    mTime: d.MTIME,
                    getTypeClass: 'name filetype-' + type,
                    clickHandler: function(item, e) {
                        toggleDetails.call(e.currentTarget);
                    }
                };
            }
            self.files.push(viewData);
        }

        /**
         * After 'addFile', this function animates the new item
         */
        self.fadeIn = function(e) {
            $(e).hide().slideDown(500);
        }

        self.fadeOutFile = function(e) {
            try {
                $(e).slideUp(500, function() {
                    e.parentNode.removeChild(e);
                });
            } catch(ex) {
                e.parentNode.removeChild(e);
            }
        }

        /**
         * Downloads the specified file (or folder zipped)
         */
        self.download = function(item, ev) {
            ev.stopPropagation(); ev.preventDefault();
            if(window.navigator.userAgent.indexOf('cloud-gui') > -1) {
                window.location.href = 'cloudfile:' + self.currentPath() + item.originalName;
                return;
            }
            $.ajax({
                type: 'POST',
                data: 'dl=' + self.currentPath() + item.originalName,
                url: '/ajax/store/download',
                dataType: 'json',
                success: function(data) {
                    window.location.href = data.url;
                }
            })
        }

        /**
         * Deletes the specified file (or folder)
         */
        self.delete = function(item, ev) {
            ev.stopPropagation(); ev.preventDefault();
            $('#modal').show();
            s = "";
            if(item.type == gettext('file')) {
                s = gettext("You are removing the file <strong>%s</strong>.");
            } else {
                s = gettext("You are removing the folder <strong>%s</strong> (and its content).");
            }

            $('#modal-container').html(interpolate(s, [item.originalName]) + " " + gettext("Are you sure?") + '<br /><input class="ok" type="button" value="' + gettext("Delete") + '" style="float: left"/><input class="cancel" type="button" value="' + gettext('Cancel') + '" style="float: right" />');
            $('#modal-container .ok').click(function() {
                $('#modal').hide();
                $.ajax({
                    type: 'POST',
                    data: 'rm=' + self.currentPath() + item.originalName,
                    url: '/ajax/store/delete',
                    dataType: 'json',
                    success: function(data) {
                        self.files.remove(item);
                    }
                })
            });
            $('#modal-container .cancel').click(function() {
                $('#modal').hide();
            });
        }

        /**
         * Renames the specified file
         */
        self.rename = function(item, e) {
            e.stopPropagation(); e.preventDefault();
            var oldName = $(e.target).parent().parent().parent().find('.name').html();
            $(e.target).parent().unbind('click').click(function(f) {
                f.stopPropagation(); f.preventDefault();
                $(e.target).parent().parent().parent().find('.name').html(oldName);
                $(e.target).parent().click(function(g) {
                    g.stopPropagation();
                    self.rename(item, g);
                });
            })
            //$(e.target).parent().parent().parent().unbind('click');
            $(e.target).parent().parent().parent().find('.name').html('<input type="text" value="' + item.originalName + '" />\
<input type="submit" value="Átnevezés" />');
            $(e.target).parent().parent().parent().find('.name input').click(function(f) {
                f.stopPropagation();
            })
            $(e.target).parent().parent().parent().find('.name input[type=submit]').click(function(e) {
                e.preventDefault();
                var newName = $(e.target).parent().parent().parent().find('.name input[type=text]').val();
                $.ajax({
                    type: 'POST',
                    data: 'path=' + self.currentPath() + item.originalName + '&new=' + newName,
                    url: '/ajax/store/rename',
                    dataType: 'json',
                    success: function(data) {
                        loadFolder(self.currentPath(), true);
                    }
                })
                return false;
            })
        }

        /**
         * Requests a new upload link from the store server
         */
        self.getUploadURL = function() {
            uploadURLRequestInProgress = true;
            $.ajax({
                type: 'POST',
                data: 'ul=' + self.currentPath() + '&next=' + encodeURI(window.location.href),
                url: '/ajax/store/upload',
                dataType: 'json',
                success: function(data) {
                    self.uploadURL(data.url);
                    uploadURLRequestInProgress = false;
                }
            })
        }

        /**
         * Creates a new folder (and then reloads the current folder)
         */
        self.newFolder = throttle(function(i, e) {
            $(e.target).parent().parent().parent().removeClass('opened');
            $.ajax({
                type: 'POST',
                data: 'new=' + self.newFolderName() + '&path=' + self.currentPath(),
                url: '/ajax/store/newFolder',
                dataType: 'json',
                success: function(data) {
                    loadFolder(self.currentPath(), true);
                }
            })
        });

        /**
         * Drag'n'drop tests
         */
        var tests = {
            filereader: typeof FileReader != 'undefined',
            dnd: 'draggable' in document.createElement('span'),
            formdata: !! window.FormData,
            progress: "upload" in new XMLHttpRequest
        };

        /**
         * Uploads the specified file(s)
         */
        var readfiles = delayUntil(function(file) {
            //1 GB file limit
            if(file.size > 1024 * 1024 * 1024) {
                $('#upload-zone').hide();
                $('#upload-error').show();
                $('#upload-error-size').show();
                setTimeout(function() {
                    $('#upload-zone').show();
                    $('#upload-error').hide();
                    $('#upload-error-size').hide();
                }, 3000);
                return;
            }
            var formData = tests.formdata ? new FormData() : null;
            formData.append('data', file);
            // now post a new XHR request
            if(tests.formdata) {
                var xhr = new XMLHttpRequest();
                var start = new Date().getTime();
                xhr.open('POST', self.uploadURL());
                xhr.onload = xhr.onerror = function() {
                    $('.file-upload').removeClass('opened');
                    $('.file-upload .details').slideUp(700);
                    $('#upload-zone').show();
                    $('#upload-progress-text').hide();
                    self.uploadProgress('0%');
                    self.uploadURL('/');
                    loadFolder(self.currentPath());
                }
                if(tests.progress) {
                    $('#upload-zone').hide();
                    $('#upload-progress-text').show();
                    var originalUsedQuota = self.quota.rawUsed();
                    xhr.upload.onprogress = function(event) {
                        if(event.lengthComputable) {
                            self.quota.rawUsed(originalUsedQuota + parseInt(event.loaded / 1024));
                            var complete = (event.loaded / event.total * 100 | 0);
                            //progress.value = progress.innerHTML = complete;
                            self.uploadProgress(complete.toFixed(1) + '%');
                            var suffix = 'B KB MB GB'.split(' ');
                            var l = event.loaded;
                            var t = event.total;
                            for(var i = 0; l > 1024; i++) {
                                l /= 1024;
                            }
                            l = l.toFixed(1) + ' ' + suffix[i];
                            for(var i = 0; t > 1024; i++) {
                                t /= 1024;
                            }
                            t = t.toFixed(1) + ' ' + suffix[i];
                            var diff = new Date().getTime() - start;
                            if(complete < 100) {
                                $('#upload-progress-text').html(gettext('Upload') + ': ' + convert(event.loaded / diff * 1000) + '/s (' + (event.loaded / event.total * 100).toFixed(2) + '%)');
                            } else {
                                $('#upload-progress-text').html(gettext('Upload') + ': ' + gettext('done, processing...'));
                            }
                        }
                    }
                }
                xhr.send(formData);
            }
        }, function() {
            return self.uploadURL() !== '/';
        }, 200);

        /**
         * Drag'n'drop listeners
         */
        document.addEventListener('drop', function(e) {
            e.stopPropagation();
            e.preventDefault();
            readfiles(e.dataTransfer.files[0]);
            return false;
        });
        document.addEventListener('dragover', function(e) {
            if(!uploadURLRequestInProgress && self.uploadURL() == '/') {
                $('.file-upload .summary').click();
            }
            e.stopPropagation();
            e.preventDefault();
            return false;
        });

        /**
         * Fetch quota information
         */

        function refreshQuota() {
            $.ajax({
                'type': 'GET',
                'url': '/ajax/store/quota',
                dataType: 'json',
                success: function(data) {
                    self.quota.rawUsed(parseInt(data.Used));
                    self.quota.rawSoft(parseInt(data.Soft));
                    self.quota.rawHard(parseInt(data.Hard));
                }
            })
        }

        //initialization
        refreshQuota();
        loadFolder(self.currentPath());
    }
    var model = new Model();
    ko.applyBindings(model);
    document.addEventListener('dragenter', function(e) {
        e.stopPropagation();
        e.preventDefault();
        return false;
    });

    document.addEventListener('drag', function(e) {
        e.stopPropagation();
        e.preventDefault();
        return false;
    });
})
