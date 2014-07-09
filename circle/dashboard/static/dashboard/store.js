$(function() {
  $("#store-list-container").on("click", ".store-list-item", function() {
    if($(this).data("item-type") == "D") {
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

  /* less js way, but at least works, tho redirection is bad */
  $("#store-list-container").on("click", '#store-upload-form input[type="submit"]', function() {
    var current_dir = $("#store-upload-form").find('[name="current_dir"]').val();
    $.get($("#store-upload-form").data("action") + "?current_dir=" + current_dir, function(result) {
      $("#store-upload-form").get(0).setAttribute("action", result['url']);
      $("#store-upload-form").submit();
    });

    return false;
  });
  
  /* click on the "fake" browse button will */
  $("#store-list-container").on("click", "#store-upload-browse", function() {
    $('#store-upload-form input[type="file"]').click();
  });
  
  $("#store-list-container").on("change", "#store-upload-file", function() {
    var input = $(this);
    var numFiles = input.get(0).files ? input.get(0).files.length : 1;
    var label = input.val().replace(/\\/g, '/').replace(/.*\//, '');
    input.trigger('fileselect', [numFiles, label]);
  });

  $("#store-list-container").on("fileselect", "#store-upload-file", function(event, numFiles, label)  {
        var input = $("#store-upload-filename");
        var log = numFiles > 1 ? numFiles + ' files selected' : label;
        if(input.length) {
            input.val(log);
        }
        if(log) {
          $('#store-upload-form input[type="submit"]').prop("disabled", false);

        } else {
          $('#store-upload-form input[type="submit"]').prop("disabled", true);
        }
  });


  /* this does not work 
  $('form input[type="submit"]').click(function() {
    var current_dir = $("form").find('[name="current_dir"]').val();
    $.get($("form").data("action") + "?current_dir=" + current_dir, function(result) {
      $.ajax({
        method: "POST",
        url: result['url'],
        data: $("form").serialize(),
        success: function(re) {
          console.log(re);
        }
      });
    });

    return false;
  }); */
    
});
