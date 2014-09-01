$(function() {
  $(".vm-details-start-template-tour").click(function() {
    ttour = createTemplateTour();
    ttour.init();
    ttour.start();
  });
});

function createTemplateTour() {
  var ttour = new Tour({
      storage: false,
      name: "template",
      template: "<div class='popover'>" +
                  "<div class='arrow'></div>" +
                  "<h3 class='popover-title'></h3>" +
                  "<div class='popover-content'></div>" +
                  "<div class='popover-navigation'>" +
                    "<div class='btn-group'>" +
                      "<button class='btn btn-sm btn-default' data-role='prev'>" +
                        '<i class="fa fa-chevron-left"></i> ' + gettext("Prev") + "</button> " +
                      "<button class='btn btn-sm btn-default' data-role='next'>" +
                        gettext("Next") + ' <i class="fa fa-chevron-right"></i></button> ' +
                      "<button class='btn btn-sm btn-default' data-role='pause-resume' data-pause-text='Pause' data-resume-text='Resume'>Pause</button> " +
                    "</div>" +
                    "<button class='btn btn-sm btn-default' data-role='end'>" +
                      gettext("End tour") + ' <i class="fa fa-flag-checkered"></i></button>' +
                  "</div>" +
                "</div>",
  });

  ttour.addStep({
    element: "#vm-details-template-tour-button",
    title: gettext("Template Tutorial Tour"),
    content: "<p>" + gettext("Welcome to the template tutorial. In this quick tour, we gonna show you how to do the steps described above.") + "</p>" +
             "<p>" + gettext('For the next tour step press the "Next" button or the right arrow (or "Back" button/left arrow for the previous step).') + "</p>" +
             "<p>" + gettext("During the tour please don't try the functions because it may lead to graphical glitches, however " +
                             "you can end the tour any time you want with the End Tour button!") + "</p>",
    placement: "bottom",
    backdrop: true,
  });

  ttour.addStep({
    backdrop: true,
    element: 'a[href="#home"]',
    title: gettext("Home tab"),
    content: gettext("In this tab you can tag your virtual machine and modify the name and description."),
    placement: 'top',
    onShow: function() {
      $('a[href="#home"]').trigger("click");
    },
  });

  ttour.addStep({
    element: 'a[href="#resources"]',
    title: gettext("Resources tab"),
    backdrop: true,
    placement: 'top',
    content: gettext("On the resources tab you can edit the CPU/RAM options and add/remove disks!"),
    onShow: function() {
      $('a[href="#resources"]').trigger("click");
    },
  });

  ttour.addStep({
    element: '#vm-details-resources-form',
    placement: 'top',
    backdrop: true,
    title: gettext("Resources"),
    content: '<p><strong>' + gettext("CPU priority") + ":</strong> " + gettext("higher is better") + "</p>" +
             '<p><strong>' + gettext("CPU count") + ":</strong> " + gettext("number of CPU cores.") + "</p>" +
             '<p><strong>' + gettext("RAM amount") + ":</strong> " + gettext("amount of RAM.") + "</p>",
    onShow: function() {
      $('a[href="#resources"]').trigger("click");
    },
  });

  ttour.addStep({
    element: '#vm-details-resources-disk',
    backdrop: true,
    placement: 'top',
    title: gettext("Disks"),
    content: gettext("You can add empty disks, download new ones and remove existing ones here."),
    onShow: function() {
      $('a[href="#resources"]').trigger("click");
    },
  });

  ttour.addStep({
    element: 'a[href="#network"]',
    backdrop: true,
    placement: 'top',
    title: gettext("Network tab"),
    content: gettext('You can add new network interfaces or remove existing ones here.'),
    onShow: function() {
      $('a[href="#network"]').trigger("click");
    },
  });


  ttour.addStep({
    element: "#ops",
    title: '<i class="fa fa-play"></i> ' + gettext("Deploy"),
    placement: "left",
    backdrop: true,
    content: gettext("Deploy the virtual machine."),
  });

  ttour.addStep({
    element: "#vm-info-pane",
    title: gettext("Connect"),
    placement: "top",
    backdrop: true,
    content: gettext("Use the connection string or connect with your choice of client!"),

  });

  ttour.addStep({
    element: "#vm-info-pane",
    placement: "top",
    title: gettext("Customize the virtual machine"),
    content: gettext("After you have connected to the virtual machine do your modifications then log off."),
  });

  ttour.addStep({
    element: "#ops",
    title: '<i class="fa fa-floppy-o"></i> ' + gettext("Save as"),
    placement: "left",
    backdrop: true,
    content: gettext('Press the "Save as template" button and wait until the activity finishes.'),
  });


  ttour.addStep({
    element: ".alert-new-template",
    title: gettext("Finish"),
    backdrop: true,
    placement: "bottom",
    content: gettext("This is the last message, if something is not clear you can do the the tour again!"),
  });

  return ttour;
}
