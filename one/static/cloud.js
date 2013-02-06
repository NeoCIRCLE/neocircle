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
    $('.wm .summary').unbind('click').click(toggleDetails);
    $('#new-wm-button').click(function() {
        $('#modal').show();
        $('#modal-container').html($('#new-wm').html());
        $('#modal-container .wm .summary').each(function() {
            this.originalHeight = parseInt($(this).next('.details').css('height'));
        })
        $('#modal-container .wm .summary').click(toggleDetails);
    });
    $('#new-template-button').click(function() {
        $('#modal').show();
        $('#modal-container').html($('#new-template').html());
    });
    $('#shadow').click(function() {
        $('#modal').hide();
    })
    $('#new-template-button').click(function() {
        $.get('/ajax/templateWizard', function(data) {
            $('#modal-container').html(data);
        })
        $('#modal').show();
    });
    $('#old-upload').click(function(e) {
        e.preventDefault();
        $(this).parent().hide().parent().find('#old-upload-form').show();
        return false;
    });
    $('.quota .used').each(function() {
        var s = this;
        $(this).css('backgroundColor', function(w) {
            return 'hsla(' + (120 - parseFloat(w) / 438 * 120).toFixed(0) + ',100%,50%,0.2)';
        }($(this).css('width')));
        if(parseInt($(this).css('width')) > 0) $(this).css('borderRight', function(w) {
            return '1px solid hsla(' + (120 - parseFloat(w) / 438 * 120).toFixed(0) + ',100%,30%,0.4)';
        }($(this).css('width')));
    });
    $('#new-folder').click(function() {
        $('#new-folder-form input')[0].focus();
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
                        if(a.type === 'fájl') {
                            return 1;
                        }
                        return -1;
                    },
                    date: function(a, b) {
                        if(a.type === b.type) {
                            return new Date(b.mTime).getTime() - new Date(a.mTime).getTime();
                        }
                        if(a.type === 'fájl') {
                            return 1;
                        }
                        return -1;
                    }
                }[self.sortBy()]);
            }

            /**
             * Loads the specified folder
             */
        var loadFolder = throttle(function(path) {
            self.currentPath(path);
            self.fileLimit = 5;
            $.ajax({
                type: 'POST',
                data: 'path=' + path,
                url: '/ajax/store/list',
                dataType: 'json',
                success: function(data) {
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
                viewData = {
                    originalName: d.NAME,
                    name: d.NAME.length > 30 ? (d.NAME.substr(0, 27) + '...') : d.NAME,
                    size: convert(d.SIZE),
                    type: 'fájl',
                    mTime: d.MTIME,
                    getTypeClass: 'name filetype-'+type,
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

        /**
         * Downloads the specified file (or folder zipped)
         */
        self.download = function(item) {
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
        self.delete = function(item) {
            $.ajax({
                type: 'POST',
                data: 'rm=' + self.currentPath() + item.originalName,
                url: '/ajax/store/delete',
                dataType: 'json',
                success: function(data) {
                    self.files.remove(item);
                }
            })
        }

        /**
         * Renames the specified file
         */
        self.rename = function(item, e) {
            var oldName = $(e.target).parent().parent().parent().find('.name').html();
            $(e.target).parent().unbind('click').click(function() {
                $(e.target).parent().parent().parent().find('.name').html(oldName);
                $(e.target).parent().click(function(e) {
                    self.rename(item, e);
                });
            })
            //$(e.target).parent().parent().parent().unbind('click');
            $(e.target).parent().parent().parent().find('.name').html('<input type="text" value="' + item.originalName + '" />\
<input type="submit" value="Átnevezés" />');
            $(e.target).parent().parent().parent().find('.name input[type=submit]').click(function(e) {
                e.preventDefault();
                var newName = $(e.target).parent().parent().parent().find('.name input[type=text]').val();
                $.ajax({
                    type: 'POST',
                    data: 'path=' + self.currentPath() + item.originalName + '&new=' + newName,
                    url: '/ajax/store/rename',
                    dataType: 'json',
                    success: function(data) {
                        loadFolder(self.currentPath());
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
                    loadFolder(self.currentPath());
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
                                $('#upload-progress-text').html('Feltöltés: ' + convert(event.loaded / diff * 1000) + '/s (' + (event.loaded / event.total * 100).toFixed(2) + '%)');
                            } else {
                                $('#upload-progress-text').html('Feltöltés: Kész, feldolgozás...');
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
