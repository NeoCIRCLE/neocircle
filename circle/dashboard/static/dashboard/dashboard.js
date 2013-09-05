$(function () {
  $('[href=#vm-graph-view]').click(function (e) {
    $('#vm-list-view').hide();
    $('#vm-graph-view').show();
    $('[href=#vm-list-view]').removeClass('disabled');
    $('[href=#vm-graph-view]').addClass('disabled');
    e.stopImmediatePropagation();
    return false;
  });
  $('[href=#vm-list-view]').click(function (e) {
    $('#vm-graph-view').hide();
    $('#vm-list-view').show();
    $('[href=#vm-list-view]').addClass('disabled');
    $('[href=#vm-graph-view]').removeClass('disabled');
    e.stopImmediatePropagation();
    return false;
  }).addClass('disabled');
  $('[title]').tooltip();
  $(':input[title]').tooltip({trigger: 'focus', placement: 'auto right'});
  $(".knob").knob();
  $("[data-slider]")
    .each(function () {
      var input = $(this);
      $("<span>")
        .addClass("output")
        .html($(this).val())
        .insertAfter(input);
    })
    .bind("slider:ready slider:changed", function (event, data) {
      $(this)
        .nextAll(".output:first")
          .html(data.value.toFixed(3));
    });
    $("[data-mark]")
        .each(function () {
            var value=$(this).attr('data-mark').parseFloat();


        });
});

