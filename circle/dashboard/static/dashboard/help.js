$(function() {
  $('.crosslink').click(function(e) {
    e.preventDefault();
    var menu = $(this).data("menu");
    $(menu).click();
    window.location = this.href;
  });

  var hash = window.location.hash;
  if(hash) {
    var pane = $(hash).closest(".tab-pane").prop("class");
    if (pane) {
      if (pane.indexOf("overview") != -1) {
        $("#overview_menu").click();
      } else {
        $("#faq_menu").click();
      }
      $("html, body").animate({scrollTop: $(hash).offset().top}, 500);
      window.location.hash = hash;
    }
  }
});
