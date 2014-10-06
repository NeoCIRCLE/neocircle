/* for functions in both vm list and vm detail */

$(function() {

  /* vm operations */
  $('#ops, #vm-details-resources-disk, #vm-details-renew-op, #vm-details-pw-reset, #vm-details-add-interface, .operation-wrapper').on('click', '.operation', function(e) {
    var icon = $(this).children("i").addClass('fa-spinner fa-spin');

    $.ajax({
      type: 'GET',
      url: $(this).attr('href'),
      success: function(data) {
        icon.removeClass("fa-spinner fa-spin");
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
        /* hide the modal we just submitted */
        $('#confirmation-modal').modal("hide");

        /* if it was successful trigger a click event on activity, this will
         *      - go to that tab
         *      - starts refreshing the activity
         */
        if(data.success) {
          $('a[href="#activity"]').trigger("click");
          if(data.with_reload) {
            // when the activity check stops the page will reload
            reload_vm_detail = true;
          }

          /* if there are messages display them */
          if(data.messages && data.messages.length > 0) {
            addMessage(data.messages.join("<br />"), data.success ? "success" : "danger");
          }
        }
        else {
          /* if the post was not successful wait for the modal to disappear
           * then append the new modal
           */
          $('#confirmation-modal').on('hidden.bs.modal', function() {
            $('body').append(data);
            $('#confirmation-modal').modal('show');
            $('#confirmation-modal').on('hidden.bs.modal', function() {
                $('#confirmation-modal').remove();
            });
          });
        }
      },
      error: function(xhr, textStatus, error) {
        $('#confirmation-modal').modal("hide");
        
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
