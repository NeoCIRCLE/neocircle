$(function() {
  "use strict";

  Util.load_scripts(["webutil.js", "base64.js", "websock.js", "des.js",
                     "input.js", "display.js", "jsunzip.js", "rfb.js"]);
  var rfb;

  function updateState(rfb, state, oldstate, msg) {
      $('#_console .btn-toolbar button').attr('disabled', (state !== "normal"));
      rfb.sendKey(0xffe3); // press and release ctrl to kill screensaver

      if (typeof(msg) !== 'undefined') {
          $('#noVNC_status').html(msg);
      }
  }

  $('a[data-toggle$="pill"][href!="#console"]').click(function() {
      if (rfb) {
          rfb.disconnect();
          rfb = 0;
      }
      $("#vm-info-pane").fadeIn();
      $("#vm-detail-pane").removeClass("col-md-12");
  });
  $('#sendCtrlAltDelButton').click(function() {
      rfb.sendCtrlAltDel(); return false;});
  $('#sendPasswordButton').click(function() {
      var pw = $("#vm-details-pw-input").val();
      for (var i=0; i < pw.length; i++) {
          rfb.sendKey(pw.charCodeAt(i));
  } return false;});


  $("body").on("click", 'a[href$="console"]', function() {
      var host, port, password, path;

      $("#vm-info-pane").hide();
      $("#vm-detail-pane").addClass("col-md-12");
      WebUtil.init_logging('warn');

      host = window.location.hostname;
      if (window.location.port == 8080) {
          port = 9999;
      } else {
          port = window.location.port === "" ? "443" : window.location.port;
      }
      password = '';
      $('#_console .btn-toolbar button').attr('disabled', true);
      $('#noVNC_status').html('Retreiving authorization token.');
      $.get(VNC_URL, function(data) {
          if (data.indexOf('vnc') !== 0) {
              $('#noVNC_status').html('No authorization token received.');
          }
          else {
              rfb = new RFB({'target': $D('noVNC_canvas'),
                             'encrypt': (window.location.protocol === "https:"),
                             'true_color':   true,
                             'local_cursor': true,
                             'shared':       true,
                             'view_only':    false,
                             'updateState':  updateState});
              rfb.connect(host, port, password, data);
      }
      }).fail(function(){
          $('#noVNC_status').html("Can't connect to console.");
      });
  });
  if (window.location.hash == "#console")
      window.onscriptsload = function(){$('a[href$="console"]').click();};
});
