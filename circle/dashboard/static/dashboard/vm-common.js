/* for functions in both vm list and vm detail */

$(function() {

  /* vm migrate */
  $('.vm-migrate').click(function(e) {
    var vm = $(this).data("vm-pk");
    $.ajax({
      type: 'GET',
      url: '/dashboard/vm/' + vm + '/migrate/', 
      success: function(data) { 
        $('body').append(data);
        $('#create-modal').modal('show');
        $('#create-modal').on('hidden.bs.modal', function() {
          $('#create-modal').remove();
        });
      }
    });
    return false;
  });
});
