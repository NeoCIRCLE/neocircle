var Websock_native; // not sure

$(function() {
  /* save resources */
  $('#vm-details-resources-save').click(function(e) {
    var error = false;
    $(".cpu-count-input, .ram-input").each(function() {
      if(!$(this)[0].checkValidity()) {
        error = true;
      }
    });
    if(error) return true;


    $('i.fa-floppy-o', this).removeClass("fa-floppy-o").addClass("fa-refresh fa-spin");
    var vm = $(this).data("vm");
    $.ajax({
      type: 'POST',
      url: $(this).parent("form").prop('action'),
      data: $('#vm-details-resources-form').serialize(),
      success: function(data, textStatus, xhr) {
        if(data.success) {
          $('a[href="#activity"]').trigger("click");
        } else {
          addMessage(data.messages.join("<br />"), "danger");
        }
        $("#vm-details-resources-save i").removeClass('fa-refresh fa-spin').addClass("fa-floppy-o");
      },
      error: function(xhr, textStatus, error) {
        $("#vm-details-resources-save i").removeClass('fa-refresh fa-spin').addClass("fa-floppy-o");
        if (xhr.status == 500) {
          addMessage("500 Internal Server Error", "danger");
        } else {
          addMessage(xhr.status + " Unknown Error", "danger");
        }
      }
    });
    e.preventDefault();
  });

  /* save as (close vnc console) */
  $('.operation-save_as_template').click(function(e) {
    if ($('li.active > a[href$="console"]').length > 0) {
      $('a[data-toggle$="pill"][href$="#activity"]').click();
    }
  });

  /* remove tag */
  $('.vm-details-remove-tag').click(function() {
    var to_remove =  $.trim($(this).parent('div').text());
    var clicked = $(this);
    $.ajax({
      type: 'POST',
      url: location.href,
      headers: {"X-CSRFToken": getCookie('csrftoken')},
      data: {'to_remove': to_remove},
      success: function(re) {
        if(re.message.toLowerCase() == "success") {
          $(clicked).closest(".label").fadeOut(500, function() {
            $(this).remove();
          });
        }
      },
      error: function() {
        addMessage(re.message, 'danger');
      }

    });
    return false;
  });

  /* for js fallback */
  $("#vm-details-pw-show").parent("div").children("input").prop("type", "password");

  /* show password */
  $("#vm-details-pw-show").click(function() {
    var input = $(this).parent("div").children("input");
    var eye = $(this).children("#vm-details-pw-eye");
    var span = $(this);

    span.tooltip("destroy");
    if(eye.hasClass("fa-eye")) {
      eye.removeClass("fa-eye").addClass("fa-eye-slash");
      input.prop("type", "text");
      input.select();
      span.prop("title", gettext("Hide password"));
    } else {
      eye.removeClass("fa-eye-slash").addClass("fa-eye");
      input.prop("type", "password");
      span.prop("title", gettext("Show password"));
    }
    span.tooltip();
  });

  /* rename */
  $("#vm-details-h1-name, .vm-details-rename-button").click(function() {
    $("#vm-details-h1-name").hide();
    $("#vm-details-rename").css('display', 'inline');
    $("#vm-details-rename-name").select();
    return false;
  });

  /* rename in home tab */
  $(".vm-details-home-edit-name-click").click(function(e) {
    $(".vm-details-home-edit-name-click").hide();
    $("#vm-details-home-rename").show();
    $("input", $("#vm-details-home-rename")).select();
    e.preventDefault();
  });

  /* rename ajax */
  $('.vm-details-rename-submit').click(function() {
    var name = $(this).parent("span").prev("input").val();
    $.ajax({
      method: 'POST',
      url: location.href,
      data: {'new_name': name},
      headers: {"X-CSRFToken": getCookie('csrftoken')},
      success: function(data, textStatus, xhr) {
        $(".vm-details-home-edit-name").text(data.new_name).show();
        $(".vm-details-home-edit-name").parent("div").show();
        $(".vm-details-home-edit-name-click").show();
        $(".vm-details-home-rename-form-div").hide();
        // update the inputs too
        $(".vm-details-rename-submit").parent("span").prev("input").val(data.new_name);
      },
      error: function(xhr, textStatus, error) {
        addMessage("Error during renaming!", "danger");
      }
    });
    return false;
  });

  /* update description click */
  $(".vm-details-home-edit-description-click").click(function(e) {
    $(".vm-details-home-edit-description-click").hide();
    $("#vm-details-home-description").show();
    var ta = $("#vm-details-home-description textarea");
    var tmp = ta.val();
    ta.val("");
    ta.focus();
    ta.val(tmp);
    e.preventDefault();
  });

  /* description update ajax */
  $('.vm-details-description-submit').click(function() {
    var description = $(this).prev("textarea").val();
    $.ajax({
      method: 'POST',
      url: location.href,
      data: {'new_description': description},
      headers: {"X-CSRFToken": getCookie('csrftoken')},
      success: function(data, textStatus, xhr) {
        var new_desc = data.new_description;
        /* we can't simply use $.text, because we need new lines */
        var tagsToReplace = {
          '&': "&amp;",
          '<': "&lt;",
          '>': "&gt;",
        };

        new_desc = new_desc.replace(/[&<>]/g, function(tag) {
          return tagsToReplace[tag] || tag;
        });

        $(".vm-details-home-edit-description")
          .html(new_desc.replace(/\n/g, "<br />"));
        $(".vm-details-home-edit-description-click").show();
        $("#vm-details-home-description").hide();
        // update the textareia
        $("vm-details-home-description textarea").text(data.new_description);
      },
      error: function(xhr, textStatus, error) {
        addMessage("Error during renaming!", "danger");
      }
    });
    return false;
  });

  // screenshot
  $("#getScreenshotButton").click(function() {
    var vm = $(this).data("vm-pk");
    var ct = $("#vm-console-screenshot");
    $("i", this).addClass("fa-spinner fa-spin");
    $(this).prop("disabled", true);
    ct.slideDown();
    var img = $("img", ct).prop("src", '/dashboard/vm/' + vm + '/screenshot/?rnd=' + Math.random());
  });

  // if the image is loaded remove the spinning stuff
  // note: this should not work if the image is cached, but it's not
  // see: http://stackoverflow.com/a/3877079/1112653
  // note #2: it actually gets cached, so a random number is appended
  $("#vm-console-screenshot img").load(function(e) {
    $("#getScreenshotButton").prop("disabled", false)
    .find("i").removeClass("fa-spinner fa-spin");

  });


  // screenshot close
  $("#vm-console-screenshot button").click(function() {
    $(this).closest("div").slideUp();
  });

  // select connection string
  $(".vm-details-connection-string-copy").click(function() {
    $(this).parent("div").find("input").select();
  });

  $("a.operation-password_reset").click(function() {
    if(Boolean($(this).data("disabled"))) return false;
  });

  $("#dashboard-tutorial-toggle").click(function() {
    var box = $("#alert-new-template");
    var list = box.find("ol");
    list.stop().slideToggle(function() {
      var url = box.find("form").prop("action");
      var hidden = list.css("display") === "none";
      box.find("button i").prop("class", "fa fa-caret-" + (hidden ? "down" : "up"));
      $.ajax({
        type: 'POST',
        url: url,
        data: {'hidden': hidden},
        headers: {"X-CSRFToken": getCookie('csrftoken')},
        success: function(re, textStatus, xhr) {}
      });
    });
    return false;
  });

  $(document).on("click", "#vm-renew-request-lease-button", function(e) {
    $("#vm-renew-request-lease").stop().slideToggle();
    e.preventDefault();
  });

  $("#vm-request-resource").click(function(e) {
    $(".cpu-priority-slider, .cpu-count-slider, .ram-slider").simpleSlider("setDisabled", false);
    $(".ram-input, .cpu-count-input, .cpu-priority-input").prop("disabled", false);

    $("#vm-details-resources-form").prop("action", $(this).prop("href"));
    $("#vm-request-resource-form").show();
    $("#modify-the-resources").show();
    $(this).hide();

    $("html, body").animate({
      scrollTop: $("#modify-the-resources").offset().top - 60
    });

    return e.preventDefault();
  });

  // Clipboard for connection strings
  if(Clipboard.isSupported())
    new Clipboard(".vm-details-connection-string-copy");
});
