/* TODO i18n
 * https://docs.djangoproject.com/en/1.5/topics/i18n/translation/#internationalization-in-javascript-code
 * TODO new tour template
 * http://bootstraptour.com/api/
 * TODO change placeholder yos
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
  });

  ttour.addStep({
    element: ".alert-new-template",
    title: "Template Tutorial Tour",
    content: "Welcome to the template tutorial. In this quick tour, we gonna show you how to do the steps described above. " +
             "For the next tour step press the Next button or the right arrow (or Back button/left arrow for the previous step). " +
             "During the tour please don't try the functions because it may lead to graphical glitches, however " +
             "you can end the tour any time you want with the End Tour button!",
    placement: "bottom",
    backdrop: true,
  });

  ttour.addStep({
    backdrop: true,
    element: 'a[href="#home"]',
    title: "Home tab", 
    content: "yo",
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
    placement: 'left',
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
    element: '.vm-details-resources-disk',
    backdrop: true,
    placement: 'left',
    title: "Disks",
    content: "jo a kontent, bar lehetne hosszabb is es akkor nem nez ki ilyen butan az end tour gomb!",
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
    backdrop: true,
    content: "Deploy the virtual machine",
  });

  ttour.addStep({
    element: "#vm-info-pane",
    title: "Connect",
    backdrop: true,
    content: "Use the connection string or connect with your choice of client!",
    
  });

  ttour.addStep({
    element: ".alert-new-template",
    placement: "bottom",
    title: "Customize the virtual machine",
    content: "Do the modifications",
  });

  ttour.addStep({
    element: ".vm-details-button-save-as",
    title: "Save",
    placement: "left",
    backdrop: true,
    content: "Press this button and wait!",
  });
  
  
  ttour.addStep({
    element: ".alert-new-template",
    title: "Fin",
    backdrop: true,
    placement: "bottom",
    content: "Congrats you managed to sit trough this exciting tour!",
  });
  
  return ttour;
}
