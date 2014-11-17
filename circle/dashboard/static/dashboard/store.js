$(function() {
  $("#store-list-container").on("click", ".store-list-item", function() {
    if($(this).data("item-type") == "D") {
      $("#store-list-up-icon").removeClass("fa-reply").addClass("fa-refresh fa-spin");
      var url = $(this).prop("href");
      $.get(url, function(result) {
        $("#store-list-container").html(result);
        noJS();
        $("[title]").tooltip();
        history.pushState({}, "", url);
      });
    } else {
      $(this).next(".store-list-file-infos").stop().slideToggle();
    }
    return false;
  });

  /* how upload works
   * - user clicks on a "fake" browse button, this triggers a click event on the file upload
   * - if the file input changes it adds the name of the file to form (or number of files if multiple is enabled)
   * - and finally when we click on the upload button (this event handler) it firsts ask the store api where to upload
   *   then changes the form's action attr before sending the form itself
   */
  $("#store-list-container").on("click", '#store-upload-form button[type="submit"]', function() {
    $('#store-upload-form button[type="submit"] i').addClass("fa-spinner fa-spin");
    var current_dir = $("#store-upload-form").find('[name="current_dir"]').val();
    $.get($("#store-upload-form").data("action") + "?current_dir=" + current_dir, function(result) {
      $("#store-upload-form").get(0).setAttribute("action", result.url);
      $("#store-upload-form").submit();
    });

    return false;
  });

  /* "fake" browse button */
  $("#store-list-container").on("click", "#store-upload-browse", function() {
    $('#store-upload-form input[type="file"]').click();
  });

  $("#store-list-container").on("change", "#store-upload-file", function() {
    var input = $(this);
    var numFiles = input.get(0).files ? input.get(0).files.length : 1;
    var label = input.val().replace(/\\/g, '/').replace(/.*\//, '');
    input.trigger('fileselect', [numFiles, label]);
  });

  $("#store-list-container").on("fileselect", "#store-upload-file", function(event, numFiles, label) {
    var input = $("#store-upload-filename");
    var log = numFiles > 1 ? numFiles + ' files selected' : label;
    if(input.length) {
      input.val(log);
    }
    if(log) {
      $('#store-upload-form button[type="submit"]').prop("disabled", false);
    } else {
      $('#store-upload-form button[type="submit"]').prop("disabled", true);
    }

  });
});
