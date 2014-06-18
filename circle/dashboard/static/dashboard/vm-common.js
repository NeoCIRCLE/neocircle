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

  /* if the operation fails show the modal again */
  $("body").on("click", "#op-form-send", function() {
    var url = $(this).closest("form").prop("action");
    $.ajax({
      url: url,
      headers: {"X-CSRFToken": getCookie('csrftoken')},
      type: 'POST',
      data: $(this).closest('form').serialize(),
      success: function(data, textStatus, xhr) {
        $('#confirmation-modal').modal("hide");

        if(data.redirect) {
          $('a[href="#activity"]').trigger("click");
        }
        else {
          var r = $('#confirmation-modal'); r.next('div').remove(); r.remove();
          $('body').append(data);
          $('#confirmation-modal').modal('show');
          $('#confirmation-modal').on('hidden.bs.modal', function() {
              $('#confirmation-modal').remove();
          });
        }
      },
      error: function(xhr, textStatus, error) {
        var r = $('#create-modal'); r.next('div').remove(); r.remove();
        
        if (xhr.status == 500) {
          addMessage("500 Internal Server Error", "danger");
        } else {
          addMessage(xhr.status + " Unknown Error", "danger");
        }
      }
    });
    return false;
  });

});
