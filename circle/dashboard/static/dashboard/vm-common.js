/* for functions in both vm list and vm detail */

$(function() {

  /* vm operations */
  $('#ops, #vm-details-resources-disk').on('click', '.operation.btn', function(e) {
    var icon = $(this).children("i").addClass('icon-spinner icon-spin');

    $.ajax({
      type: 'GET',
      url: $(this).attr('href'),
      success: function(data) {
        icon.removeClass("icon-spinner icon-spin");
        $('body').append(data);
        $('#confirmation-modal').modal('show');
        $('#confirmation-modal').on('hidden.bs.modal', function() {
          $('#confirmation-modal').remove();
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
