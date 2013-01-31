var toggleDetails;
$(function(){
    function getCookie(name) {
        var cookieValue = null;
        if (document.cookie && document.cookie != '') {
            var cookies = document.cookie.split(';');
            for (var i = 0; i < cookies.length; i++) {
                var cookie = jQuery.trim(cookies[i]);
                if (cookie.substring(0, name.length + 1) == (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    var csrftoken = getCookie('csrftoken');
    function csrfSafeMethod(method) {
        return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
    }
    $.ajaxSetup({
        crossDomain: false,
        beforeSend: function(xhr, settings) {
            if (!csrfSafeMethod(settings.type)) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            }
        }
    });
    toggleDetails=function(){
      if($(this).next('.details').is(':hidden')){
            $(this).next('.details').slideDown(700);
            $(this).parent('.wm').addClass('opened');
        } else {
            var that=this;
            $(this).next('.details').slideUp(700,function(){
                $(that).parent('.wm').removeClass('opened');
            });
        }
    }
    $('.wm .summary').unbind('click').click(toggleDetails);
    $('#load-more-files').click(function(){
        $('.actions', this).show();
        var that=this;
        setTimeout(function(){
            $(that).prev('li').slideDown(500,function(){
                $('.actions', that).hide();
            });
        },2000);
    })
    $('#new-wm-button').click(function(){
        $('#modal').show();
        $('#modal-container').html($('#new-wm').html());
        $('#modal-container .wm .summary').each(function(){
            this.originalHeight=parseInt($(this).next('.details').css('height'));
        })
        $('#modal-container .wm .summary').click(toggleDetails);
        });
    $('#new-template-button').click(function(){
        $('#modal').show();
        $('#modal-container').html($('#new-template').html());
    });
    $('#shadow').click(function(){
        $('#modal').hide();
    })
    $('#new-template-button').click(function(){
        $.get('/ajax/templateWizard', function(data){
            $('#modal-container').html(data);
        })
        $('#modal').show();
    });
    var Model=function(){
        var self=this;
        self.files=ko.observableArray();
        self.allFiles=[];
        self.notInRoot=ko.observable(false);
        self.fileLimit=5;
        self.jumpUp=function(){
            var s=self.currentPath();
            self.currentPath(s.substr(0,s.substr(0,s.length-1).lastIndexOf('/')+1));
            loadFolder(self.currentPath());
        }
        var loadFolder=function(path){
            self.fileLimit=5;
            $.ajax({
                type: 'POST',
                data: 'path='+path,
                url: '/ajax/store/list',
                dataType: 'json',
                success: function(data){
                    $('.file-list .real').css({left:0,position:'relative'}).animate({left:'-100%'},500).promise().done(function(){
                        loadFolderDone(data);
                        $('.file-list .real').css({left:'-300%',position:'relative'}).animate({left:0},500);
                    });
                },
            })
        }
        var loadFolderDone=function(data){
            self.notInRoot(self.currentPath().lastIndexOf('/') !== 0);
            self.files([]);
            self.allFiles=data;
            var viewData=[];
            var added=0;
            for(var i in data){
                added++;
                if(added<6)
                    addFile(data[i]);
            }
        }
        var addFile=function(d){
            var viewData;
            if(d.TYPE === 'D'){
                viewData={
                    originalName: d.NAME,
                    name: d.NAME.length>30?(d.NAME.substr(0,27)+'...'):d.NAME,
                    size: 'katalógus',
                    type: 'katalógus',
                    mTime: d.MTIME,
                    getTypeClass: 'name filetype-folder',
                    clickHandler: function(item){
                        self.currentPath(self.currentPath()+item.originalName+'/');
                        loadFolder(self.currentPath());
                    }
                };
            } else {
                viewData={
                    originalName: d.NAME,
                    name: d.NAME.length>30?(d.NAME.substr(0,27)+'...'):d.NAME,
                    size: d.SIZE+'K',
                    type: 'fájl',
                    mTime: d.MTIME,
                    getTypeClass: 'name filetype-text',
                    clickHandler: function(item, event){
                    }
                };
            }
            self.files.push(viewData);
        }
        self.fadeIn=function(e){
            console.log(e,arguments);
            $(e).hide().slideDown(500);
        }
        self.currentPath=ko.observable('/');
        self.showMore=function(){
            for(var i=self.fileLimit;i<self.fileLimit+5;i++){
                if(self.allFiles[i] === undefined) break;
                addFile(self.allFiles[i]);
            }
            self.fileLimit+=5;
        }
        self.download=function(item){
            $.ajax({
                type: 'POST',
                data: 'dl='+self.currentPath()+item.originalName,
                url: '/ajax/store/download',
                dataType: 'json',
                success: function(data){
                    window.location.href=data.url;
                }
            })
        }
        self.delete=function(item){
             $.ajax({
                type: 'POST',
                data: 'rm='+self.currentPath()+item.originalName,
                url: '/ajax/store/delete',
                dataType: 'json',
                success: function(data){
                    loadFolder(self.currentPath());
                }
            })
        }
        loadFolder(self.currentPath());
    }
    var model=new Model();
    ko.applyBindings(model);
    document.addEventListener('dragenter', function(e){console.log(e);e.stopPropagation();e.preventDefault();return false;});
    document.addEventListener('dragover', function(e){console.log(e);e.stopPropagation();e.preventDefault();return false;});
    document.addEventListener('drop', function(e){console.log(e);e.stopPropagation();e.preventDefault();return false;});
})
