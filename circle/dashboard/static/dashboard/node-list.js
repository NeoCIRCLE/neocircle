$(function() {
  $(document).ready( function() {
    // find disabled nodes, set danger (red) on the rows
    $('.node-disabled').closest("tr").addClass('danger');
  });
  $('#reschedule-now').click(function() {
    $.get($(this).attr('href'), function(data){
      highlight = data.result === 'ok' ? 'success' : 'danger';
      addMessage(data.message, highlight);
    });
    return false;
  });
});
