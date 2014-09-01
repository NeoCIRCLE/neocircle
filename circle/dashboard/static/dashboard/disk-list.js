$(function() {
  $(".disk-list-disk-percentage").each(function() {
    var disk = $(this).data("disk-pk");
    var element = $(this);
    refreshDisk(disk, element);
  });
});

function refreshDisk(disk, element) {
    $.get("/dashboard/disk/" + disk + "/status/", function(result) {
      if(result.percentage === null || result.failed == "True") {
        location.reload();
      } else {
        var diff = result.percentage - parseInt(element.html());
        var refresh = 5 - diff;
        refresh = refresh < 1 ? 1 : (result.percentage === 0 ? 1 : refresh);
        if(isNaN(refresh)) refresh = 2; // this should not happen

        element.html(result.percentage);
        setTimeout(function() {refreshDisk(disk, element);}, refresh * 1000);
      }
    });
}
