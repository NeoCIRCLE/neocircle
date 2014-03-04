/* for functions in both vm list and vm detail */

$(function() {

  /* vm migrate */
  $('.vm-migrate').click(function(e) {
    var icon = $(this).children("i");
    var vm = $(this).data("vm-pk");
    icon.removeClass("icon-truck").addClass("icon-spinner icon-spin");

    $.ajax({
      type: 'GET',
      url: '/dashboard/vm/' + vm + '/migrate/', 
      success: function(data) {
        icon.addClass("icon-truck").removeClass("icon-spinner icon-spin");
        $('body').append(data);
        $('#create-modal').modal('show');
        $('#create-modal').on('hidden.bs.modal', function() {
          $('#create-modal').remove();
        });
        $('#vm-migrate-node-list li').click(function(e) {
          var li = $(this).closest('li');
          if (li.find('input').attr('disabled'))
            return true;
          $('#vm-migrate-node-list li').removeClass('panel-primary');
          li.addClass('panel-primary').find('input').attr('checked', true);
          return false;
        });
        $('#vm-migrate-node-list li input:checked').closest('li').addClass('panel-primary');
      }
    });
    return false;
  });
});
