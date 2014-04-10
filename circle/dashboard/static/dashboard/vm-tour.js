/* TODO i18n
 * https://docs.djangoproject.com/en/1.5/topics/i18n/translation/#internationalization-in-javascript-code
 */
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
                        '<i class="icon-chevron-left"></i> ' + "Prev" + "</button> " +
                      "<button class='btn btn-sm btn-default' data-role='next'>" +
                        'Next' + ' <i class="icon-chevron-right"></i></button> ' +
                      "<button class='btn btn-sm btn-default' data-role='pause-resume' data-pause-text='Pause' data-resume-text='Resume'>Pause</button> " +
                    "</div>" +
                    "<button class='btn btn-sm btn-default' data-role='end'>" +
                      "End tour" + ' <i class="icon-flag-checkered"></i></button>' +
                  "</div>" +
                "</div>",
  });

  ttour.addStep({
    element: ".alert-new-template",
    title: "Template Tutorial Tour",
    content: "<p>Welcome to the template tutorial. In this quick tour, we gonna show you how to do the steps described above.</p>" +
             '<p>For the next tour step press the "Next" button or the right arrow (or "Back" button/left arrow for the previous step).</p>' +
             "<p>During the tour please don't try the functions because it may lead to graphical glitches, however " +
             "you can end the tour any time you want with the End Tour button!</p>",
    placement: "bottom",
    backdrop: true,
  });

  ttour.addStep({
    backdrop: true,
    element: 'a[href="#home"]',
    title: "Home tab", 
    content: "In this tab you can tag your virtual machine and modify the description.",
    placement: 'top',
    onShow: function() {
      console.log("yosag van");
      $('a[href="#home"]').trigger("click");
    },
  });

  ttour.addStep({
    element: 'a[href="#resources"]',
    title: "Resources tab",
    backdrop: true,
    placement: 'top',
    content: "On the resources tab you can edit the CPU/RAM options and add/remove disks!",
    onShow: function() {
      $('a[href="#resources"]').trigger("click");
    },
  });

  ttour.addStep({
    element: '#vm-details-resources-form',
    placement: 'top',
    backdrop: true,
    title: "Resources",
    content: '<p><strong>CPU priority:</strong> higher (or lower?) is better</p>' + 
             '<p><strong>CPU count:</strong> yooo</p>' +
             '<p><strong>RAM amount:</strong> yoo RAM</p>', 
    onShow: function() {
      $('a[href="#resources"]').trigger("click");
    },
  });

  ttour.addStep({
    element: '#vm-details-resources-disk',
    backdrop: true,
    placement: 'top',
    title: "Disks",
    content: "You can add empty disks, download new ones and remove existing ones here.",
    onShow: function() {
      $('a[href="#resources"]').trigger("click");
    },
  });

  ttour.addStep({
    element: 'a[href="#network"]',
    backdrop: true,
    placement: 'top',
    title: "Network tab",
    content: 'You can add new network interfaces or remove existing ones here.',
    onShow: function() {
      $('a[href="#network"]').trigger("click");
    },
  });


  ttour.addStep({
    element: "#vm-details-button-deploy",
    title: "Deploy",
    placement: "left",
    backdrop: true,
    content: "Deploy the virtual machine",
  });

  ttour.addStep({
    element: "#vm-info-pane",
    title: "Connect",
    placement: "top",
    backdrop: true,
    content: "Use the connection string or connect with your choice of client!",
    
  });

  ttour.addStep({
    element: ".alert-new-template",
    placement: "bottom",
    title: "Customize the virtual machine",
    content: "After you have connected to the virtual do you modifications",
  });

  ttour.addStep({
    element: ".vm-details-button-save-as",
    title: "Save",
    placement: "left",
    backdrop: true,
    content: 'Press the "Save as template" button and wait until the activity finishes.',
  });
  
  
  ttour.addStep({
    element: ".alert-new-template",
    title: "Finisih",
    backdrop: true,
    placement: "bottom",
    content: "This is the last message, if something is not clear you can do the the tour again!",
  });
  
  return ttour;
}
