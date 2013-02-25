var cloud = (function(cloud) {
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
            return cloud.convert(self.quota.rawUsed(), 1);
        });
        self.quota.hard = ko.computed(function() {
            return cloud.convert(self.quota.rawHard(), 1);
        });
        self.quota.soft = ko.computed(function() {
            return cloud.convert(self.quota.rawSoft(), 1);
        });
        self.quota.usedBar = ko.computed(function() {
            return (self.quota.rawUsed() / self.quota.rawHard() * 100).toFixed(0) + '%';
        }, self);
        self.quota.softPos = ko.computed(function() {
            return (self.quota.rawSoft() / self.quota.rawHard() * 100).toFixed(0) + '%';
        }, self);
        self.sortBy = ko.observable('name');

        $('#current-location select').on('change', function() {
            self.sortBy($('#current-location select').val());
            sortFiles();
        })

        /**
         * Loads the parent folder
         */
        self.jumpUp = function() {
            var s = self.currentPath();
            loadFolder(s.substr(0, s.substr(0, s.length - 1).lastIndexOf('/') + 1));
        };

        var sortFiles = (function() {
            self.files.sort({
                name: function(a, b) {
                    if (a.type === b.type) {
                        return a.originalName.localeCompare(b.originalName);
                    }
                    if (a.type === gettext('file')) {
                        return 1;
                    }
                    return -1;
                },
                date: function(a, b) {
                    if (a.type === b.type) {
                        return new Date(b.mTime).getTime() - new Date(a.mTime).getTime();
                    }
                    if (a.type === gettext('file')) {
                        return 1;
                    }
                    return -1;
                },
                size: function(a, b) {
                    if (a.type === b.type) {
                        return b.originalSize - a.originalSize;
                    }
                    if (a.type === gettext('file')) {
                        return 1;
                    }
                    return -1;
                },
            }[self.sortBy()]);
        });

        /**
         * Loads the specified folder
         */
        var loadFolder = cloud.throttle(function(path, fast) {
            self.currentPath(path);
            $.ajax({
                type: 'POST',
                data: 'path=' + path,
                url: '/ajax/store/list',
                dataType: 'json',
                success: function(data) {
                    if (!fast) {
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
        });

        self.loadTopList = cloud.throttle(function() {
            self.currentPath('/');
            $.ajax({
                type: 'POST',
                url: '/ajax/store/top/',
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
                }
            })
        });

        /**
         * After loadFolder completes, this function updates the UI
         */

        function loadFolderDone(data) {
            var viewData = [];
            var added = 0;
            self.notInRoot(self.currentPath().lastIndexOf('/') !== 0);
            self.files([]);
            for (var i in data) {
                addFile(data[i]);
            }
            sortFiles();
        }

        /**
         * Add file to the displayed files list
         */

        function addFile(d) {
            var viewData;
            if (d.TYPE === 'D') {
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
                for (var i in ext) {
                    if (d.NAME.match(ext[i])) {
                        type = i;
                        break;
                    }
                }
                var extension;
                try {
                    extension = d.NAME.match(/\.\w+$/)[0].substr(1);
                } catch (ex) {
                    extension = 'N/A';
                }
                viewData = {
                    originalName: d.NAME,
                    originalSize: d.SIZE,
                    name: d.NAME.length > 30 ? (d.NAME.substr(0, 20) + '... (' + extension + ')') : d.NAME,
                    size: cloud.convert(d.SIZE),
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
            //firefox sucks :S
            try {
                $(e).hide().slideDown(500);
            } catch (ex) {

            }
        }

        self.fadeOutFile = function(e) {
            try {
                $(e).slideUp(500, function() {
                    e.parentNode.removeChild(e);
                });
            } catch (ex) {
                e.parentNode.removeChild(e);
            }
        }

        /**
         * Downloads the specified file (or folder zipped)
         */
        self.download = function(item, ev) {
            ev.stopPropagation();
            ev.preventDefault();
            if (window.navigator.userAgent.indexOf('cloud-gui') > -1) {
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
            ev.stopPropagation();
            ev.preventDefault();
            $('#modal').show();
            s = "";
            if (item.type == gettext('file')) {
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
            e.stopPropagation();
            e.preventDefault();
            var oldName = $(e.target).parent().parent().parent().find('.name').html();
            $(e.target).parent().unbind('click').click(function(f) {
                f.stopPropagation();
                f.preventDefault();
                $(e.target).parent().parent().parent().find('.name').html(oldName);
                $(e.target).parent().click(function(g) {
                    g.stopPropagation();
                    self.rename(item, g);
                });
            })
            //$(e.target).parent().parent().parent().unbind('click');
            $(e.target).parent().parent().parent().find('.name').html('<input type="text" value="' + item.originalName + '" />\
<input type="submit" value="' + gettext('Rename') + '" />');
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
        self.newFolder = cloud.throttle(function(i, e) {
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
        var readfiles = cloud.delayUntil(function(file, next) {
            console.log('read', next)
            //1 GB file limit
            if (file.size > 1024 * 1024 * 1024) {
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
            if (tests.formdata) {
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
                if (tests.progress) {
                    $('#upload-zone').hide();
                    $('#upload-progress-text').show();
                    var originalUsedQuota = self.quota.rawUsed();
                    xhr.upload.onprogress = function(event) {
                        if (event.lengthComputable) {
                            self.quota.rawUsed(originalUsedQuota + parseInt(event.loaded / 1024));
                            var complete = (event.loaded / event.total * 100 | 0);
                            //progress.value = progress.innerHTML = complete;
                            self.uploadProgress(complete.toFixed(1) + '%');
                            var suffix = 'B KB MB GB'.split(' ');
                            var l = event.loaded;
                            var t = event.total;
                            for (var i = 0; l > 1024; i++) {
                                l /= 1024;
                            }
                            l = l.toFixed(1) + ' ' + suffix[i];
                            for (var i = 0; t > 1024; i++) {
                                t /= 1024;
                            }
                            t = t.toFixed(1) + ' ' + suffix[i];
                            var diff = new Date().getTime() - start;
                            if (complete < 100) {
                                $('#upload-progress-text').html(gettext('Upload') + ': ' + cloud.convert(event.loaded / diff * 1000) + '/s (' + (event.loaded / event.total * 100).toFixed(2) + '%)');
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
            if (!uploadURLRequestInProgress && self.uploadURL() == '/') {
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
    $(function() {
        ko.applyBindings(model);
        $('#keys').click(function(e) {
            $('.key').slideDown(700);
            $('#keys').slideUp(700);
        });
    });
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
    return cloud;
})(cloud || {});
