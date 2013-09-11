$('i[class="icon-remove"]').click(function() {
    href = $(this).parent('a').attr('href');
    csrf = getCookie('csrftoken');
    var click_this = this;

    host = $('.page-header').children('h2').text()
    group = $(this).closest('h4').text();

    if(group.length > 0) {
        text = gettext('Are you sure you want to remove host group <strong>"%(group)s"</strong> from <strong>"%(host)s"</strong>?');
        s = interpolate(text, {'group': group, 'host': host}, true);
    } else {
        s = gettext('Are you sure you want to delete this rule?');
    }

    bootbox.dialog({
        message: s,
        buttons: {
            cancel: {
                'label': "Cancel",
                'className': "btn-info",
                'callback': function () {}
            },
            remove: {
                'label': "Remove",
                'className': "btn-danger",
                'callback': function() {
                    delete_rule_or_group(click_this);
                }
            }
        }
    });
    return false;
});


function delete_rule_or_group(click_this) {
    ajax = $.ajax({
        type: 'POST',
        url: href,
        headers: {"X-CSRFToken": csrf},
        context: click_this,
        success: function(data, textStatus, xhr) {
            if(xhr.status == 200) {
                // we delete a row in a table
                if(href.indexOf("rules") != -1) {
                    $(this).closest('tr').fadeOut(500, function() {
                        $(this).remove();
                    });
                } 
                // we delete the whole div around the table
                else {
                    // we need to readd the deleted group to the select
                    group_pk = parseInt($(this).closest('h4').attr('id'));
                    group_name = $(this).closest('h4').text();
                    
                    $(this).closest('div').fadeOut(500, function() {
                        $(this).remove();
                        $('#add_group')
                            .append($("<option></option>")
                            .attr('value', group_pk)
                            .text(group_name));
                    });
                }
            }
        }
    });
    return false;
}
