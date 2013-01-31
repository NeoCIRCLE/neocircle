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
        self.notInRoot=ko.observable(false);
        self.jumpUp=function(){
            var s=self.currentPath();
            self.currentPath(s.substr(0,s.substr(0,s.length-1).lastIndexOf('/')+1));
            loadFolder(self.currentPath());
        }
        var loadFolder=function(path){
            console.log('loadFolder');
            $.ajax({
                type: 'POST',
                data: 'path='+path,
                url: '/ajax/store/list',
                dataType: 'json',
                success: function(data){
                    $('.file-list .real').css({left:0,position:'relative'}).animate({left:'-100%'},1000).promise().done(function(){
                        loadFolderDone(data);
                        $('.file-list .real').css({left:'-300%',position:'relative'}).animate({left:0},1000);
                    });
                },
            })
        }
        var loadFolderDone=function(data){
            self.notInRoot(self.currentPath().lastIndexOf('/') !== 0);
            var viewData=[];
            for(var i in data){
                var d=data[i];
                if(data[i].TYPE === 'D'){
                    viewData[i]={
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
                    viewData[i]={
                        name: d.NAME.length>30?(d.NAME.substr(0,27)+'...'):d.NAME,
                        size: data[i].SIZE+'K',
                        type: 'fájl',
                        mTime: d.MTIME,
                        getTypeClass: 'name filetype-text',
                        clickHandler: function(){

                        }
                    };
                }
            }
            self.files(viewData);
        }
        self.currentPath=ko.observable('/');
        loadFolder(self.currentPath());
    }
    var model=new Model();
    ko.applyBindings(model);
    document.addEventListener('dragenter', function(e){console.log(e);e.stopPropagation();e.preventDefault();return false;});
    document.addEventListener('dragover', function(e){console.log(e);e.stopPropagation();e.preventDefault();return false;});
    document.addEventListener('drop', function(e){console.log(e);e.stopPropagation();e.preventDefault();return false;});
})
