$('i[class="icon-remove"]').click(function() {
    href = $(this).parent('a').attr('href');
    csrf = getCookie('csrftoken');
    var click_this = this;

    group = $(this).closest('h4').text();

    s = gettext('Are you sure you want to delete this device?');

    bootbox.dialog({
        message: s,
        buttons: {
            cancel: {
                'label': gettext("Cancel"),
                'className': "btn-info",
                'callback': function () {}
            },
            remove: {
                'label': gettext("Remove"),
                'className': "btn-danger",
                'callback': function() {
                    delete_device(click_this);
                }
            }
        }
    });
    return false;
});


function delete_device(click_this) {
    ajax = $.ajax({
        type: 'POST',
        url: href,
        headers: {"X-CSRFToken": csrf},
        context: click_this,
        success: function(data, textStatus, xhr) {
            if(xhr.status == 200) {
                  $(this).closest('tr').fadeOut(500, function() {
                      $(this).remove();
                  });
            }
        }
    });
    return false;
}
