
$(function() {
  $('.crosslink').click(function(e) {
    e.preventDefault();
    var menu = $(this).data("menu");
    $(menu).click();
    window.location = this.href;
  });

  var hash = window.location.hash;
  if(hash) {
    var menu;
    if($(hash).closest(".tab-pane").prop("class").indexOf("overview") != -1) {
      menu = "#overview_menu"
    } else {
      menu = "#faq_menu"
    }
    $(menu).click();
    $("html, body").animate({scrollTop: $(hash).offset().top}, 500);
    window.location.hash = hash;
  }
});
