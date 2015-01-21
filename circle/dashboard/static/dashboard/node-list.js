$(function() {
  $(document).ready( function() {
    colortable();
  });

  // find disabled nodes, set danger (red) on the rows
  function colortable()
  {
	$('.false').closest("tr").addClass('danger');
	$('.true').closest("tr").removeClass('danger');
  }
});
