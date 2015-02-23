$(function() {
  $(document).ready( function() {
    // find disabled nodes, set danger (red) on the rows
    $('.node-disabled').closest("tr").addClass('danger');
  });
});
