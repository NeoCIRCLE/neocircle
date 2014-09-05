$(function() {
  $(".vm-details-start-template-tour").click(function() {
    var intro = introJs();
    intro.setOptions({
      'nextLabel': gettext("Next"),
      'prevLabel': gettext("Previous"),
      'skipLabel': gettext("Skip"),
      'doneLabel': gettext("Done"),
    });
    intro.setOptions({
      steps: [
        {
          element: document.querySelector("#vm-details-template-tour-button"),
          intro: "<p>" + gettext("Welcome to the template tutorial. In this quick tour, we gonna show you how to do the steps described above.") + "</p>" +
                 "<p>" + gettext('For the next tour step press the "Next" button or the right arrow (or "Back" button/left arrow for the previous step).') + "</p>" +
                 "<p>" + gettext("During the tour please don't try the functions because it may lead to graphical glitches, however " +
                                 "you can end the tour any time you want with the End Tour button!") + "</p>",
        },
        {
          element: document.querySelector('a[href="#home"]'),
          intro: gettext("In this tab you can tag your virtual machine and modify the name and description."),
        },
        {
          element: document.querySelector('a[href="#resources"]'),
          intro: gettext("On the resources tab you can edit the CPU/RAM options and add/remove disks!"),
        },
        {
          element: document.querySelector('#vm-details-resources-form'),
          intro: '<p><strong>' + gettext("CPU priority") + ":</strong> " + gettext("higher is better") + "</p>" + 
                   '<p><strong>' + gettext("CPU count") + ":</strong> " + gettext("number of CPU cores.") + "</p>" +
                   '<p><strong>' + gettext("RAM amount") + ":</strong> " + gettext("amount of RAM.") + "</p>", 
        },
        {
          element: document.querySelector('#vm-details-resources-disk'),
          intro: gettext("You can add empty disks, download new ones and remove existing ones here."),
        },
        {
          element: document.querySelector('a[href="#network"]'),
          intro: gettext('You can add new network interfaces or remove existing ones here.'),
        },
        {
          element: document.querySelector("#ops"),
          intro: gettext("Deploy the virtual machine."),
        },
        {
          element: document.querySelector("#vm-info-pane"),
          intro: gettext("Use the connection string or connect with your choice of client!"),
        },
        {
          element: document.querySelector("#vm-info-pane"),
          intro: gettext("After you have connected to the virtual machine do your modifications then log off."),
        },
        {
          element: document.querySelector("#ops"),
          intro: gettext('Press the "Save as template" button and wait until the activity finishes.'),
        },
        {
          element: document.querySelector(".alert-new-template"),
          intro: gettext("This is the last message, if something is not clear you can do the the tour again!"),
        },
      ]
    });
    intro.onbeforechange(function(target) {
      /* if the tab menu item is highlighted */
      if($(target).data("toggle") == "pill") {
        $(target).trigger("click");
      }

      /* if anything in a tab is highlighted change to that tab */
      var tab = $(target).closest('.tab-pane:not([id^="ipv"])');
      var id = tab.prop("id");
      if(id) {
        id = id.substring(1, id.length);
        $('a[href="#' + id + '"]').trigger("click");
      }
    });
    intro.start();

    return false;
  });
});
