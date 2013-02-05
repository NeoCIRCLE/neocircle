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
    $('#load-more-files').click(function() {
        $('.actions', this).show();
        var that = this;
        setTimeout(function() {
            $(that).prev('li').slideDown(500, function() {
                $('.actions', that).hide();
            });
        }, 2000);
    })
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
    })

    function Model() {
        var self = this;
        self.files = ko.observableArray();
        self.allFiles = [];
        self.notInRoot = ko.observable(false);
        self.fileLimit = 5;

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
        self.jumpUp = function() {
            var s = self.currentPath();
            loadFolder(s.substr(0, s.substr(0, s.length - 1).lastIndexOf('/') + 1));
        }
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

        function loadFolderDone(data) {
                var viewData = [];
                var added = 0;
                self.notInRoot(self.currentPath().lastIndexOf('/') !== 0);
                self.files([]);
                self.allFiles = data;
                for(var i in data) {
                    added++;
                    if(added < 6) addFile(data[i]);
                }
            }

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
                viewData = {
                    originalName: d.NAME,
                    name: d.NAME.length > 30 ? (d.NAME.substr(0, 27) + '...') : d.NAME,
                    size: d.SIZE + 'K',
                    type: 'fájl',
                    mTime: d.MTIME,
                    getTypeClass: 'name filetype-text',
                    clickHandler: function(item, event) {}
                };
            }
            self.files.push(viewData);
        }
        self.fadeIn = function(e) {
            $(e).hide().slideDown(500);
        }
        self.currentPath = ko.observable('/');
        self.showMore = function() {
            for(var i = self.fileLimit; i < self.fileLimit + 5; i++) {
                if(self.allFiles[i] === undefined) break;
                addFile(self.allFiles[i]);
            }
            self.fileLimit += 5;
        }
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
        self.delete = function(item) {
            $.ajax({
                type: 'POST',
                data: 'rm=' + self.currentPath() + item.originalName,
                url: '/ajax/store/delete',
                dataType: 'json',
                success: function(data) {
                    loadFolder(self.currentPath());
                }
            })
        }
        self.rename = function(item, e) {
            $(e.target).parent().parent().parent().unbind('click');
            $(e.target).parent().parent().parent().find('.name').html('<input type="text" value="' + item.originalName + '" />\
<input type="submit" value="Átnevezés" />');
            $(e.target).parent().parent().parent().find('.name input[type=submit]').click(function() {
                var newName = $(e.target).parent().parent().parent().find('.name input[type=text]').val();
                loadFolder(self.currentPath());
            })
        }
        self.uploadURL = ko.observable('/');
        self.getUploadURL = function() {
            $.ajax({
                type: 'POST',
                data: 'ul=' + self.currentPath() + '&next=' + encodeURI(window.location.href),
                url: '/ajax/store/upload',
                dataType: 'json',
                success: function(data) {
                    self.uploadURL(data.url);
                }
            })
        }
        self.newFolderName = ko.observable();
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
        self.uploadProgress = ko.observable('0%');
        var tests = {
            filereader: typeof FileReader != 'undefined',
            dnd: 'draggable' in document.createElement('span'),
            formdata: !! window.FormData,
            progress: "upload" in new XMLHttpRequest
        };

        function readfiles(files) {
            var formData = tests.formdata ? new FormData() : null;
            for(var i = 0; i < files.length; i++) {
                if(tests.formdata) formData.append('data', files[i]);
            }
            // now post a new XHR request
            if(tests.formdata) {
                var xhr = new XMLHttpRequest();
                xhr.open('POST', self.uploadURL());
                xhr.onload = function() {
                    $('.file-upload').removeClass('opened');
                    $('.file-upload .details').slideUp(700);
                    $('#upload-zone').show();
                    $('#upload-progress-text').hide();
                    self.uploadProgress('0%');
                    self.uploadURL('/');
                    loadFolder(self.currentPath());
                };
                xhr.onerror = function() {
                    $('.file-upload').removeClass('opened');
                    $('.file-upload .details').slideUp(700);
                    $('#upload-zone').show();
                    $('#upload-progress-text').hide();
                    self.uploadProgress('0%');
                    self.uploadURL('/');
                }
                if(tests.progress) {
                    $('#upload-zone').hide();
                    $('#upload-progress-text').show();
                    var originalUsedQuota=self.quota.rawUsed();
                    xhr.upload.onprogress = function(event) {
                        if(event.lengthComputable) {
                            self.quota.rawUsed(originalUsedQuota+parseInt(event.loaded/1024));
                            var complete = (event.loaded / event.total * 100 | 0);
                            //progress.value = progress.innerHTML = complete;
                            self.uploadProgress(parseInt(complete) + '%');
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
                            if(complete < 100) {
                                $('#upload-progress-text').html('Feltöltés: ' + l + '/' + t + ' (' + (event.loaded / event.total * 100).toFixed(2) + '%)');
                            } else {
                                $('#upload-progress-text').html('Feltöltés: Mindjárt kész...');
                            }
                        }
                    }
                }

                xhr.send(formData);
            }
        }
        document.addEventListener('drop', function(e) {
            e.stopPropagation();
            e.preventDefault();
            readfiles(e.dataTransfer.files);
            return false;
        });
        self.quota = {
            rawUsed: ko.observable(0),
            rawSoft: ko.observable(0),
            rawHard: ko.observable(0)
        };
        self.quota.used=ko.computed(function(){
            var suffix = 'KB MB GB'.split(' ');
            var l=self.quota.rawUsed();
            for(var i = 0; l > 1024; i++) {
                l /= 1024;
            }
            return l.toFixed(1)+' '+suffix[i];
        });
        self.quota.hard=ko.computed(function(){
            var suffix = 'KB MB GB'.split(' ');
            var l=self.quota.rawHard();
            for(var i = 0; l > 1024; i++) {
                l /= 1024;
            }
            return l.toFixed(1)+' '+suffix[i];
        });
        self.quota.soft=ko.computed(function(){
            var suffix = 'KB MB GB'.split(' ');
            var l=self.quota.rawSoft();
            for(var i = 0; l > 1024; i++) {
                l /= 1024;
            }
            return l.toFixed(1)+' '+suffix[i];
        });
        self.quota.usedBar = ko.computed(function() {
            return(self.quota.rawUsed() / self.quota.rawHard() * 100).toFixed(0) + '%';
        }, self);
        self.quota.softPos = ko.computed(function() {
            return(self.quota.rawSoft() / self.quota.rawHard() * 100).toFixed(0) + '%';
        }, self)

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
    document.addEventListener('dragover', function(e) {
        e.stopPropagation();
        e.preventDefault();
        return false;
    });

})
