var toggleDetails;
$(function(){
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
        $.ajax({
            type: 'POST',
            url: '/ajax/store/list',
            dataType: 'json',
        }).done(function(data){
            for(var i in data){
                data[i].getTypeClass=function(t){
                    return 'name filetype-'+(t=='D'?'folder':'text');
                }(data[i].TYPE);
                data[i].SIZE=data[i].TYPE=='D'?'katalógus':(data[i].SIZE+'K');
                data[i].TYPE=data[i].TYPE=='D'?'katalógus':'fájl';
            }
            self.files(data);
            $('.wm .summary').unbind('click').click(toggleDetails);
        })
    }
    var model=new Model();
    ko.applyBindings(model);
})
