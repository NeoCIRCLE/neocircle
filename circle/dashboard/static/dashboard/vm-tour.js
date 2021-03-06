var intro;
$(function() {
  $("#vm-details-start-template-tour").click(function() {
    intro = introJs();
    intro.setOptions({
      'nextLabel': gettext("Next") + ' <i class="fa fa-chevron-right"></i>',
      'prevLabel': '<i class="fa fa-chevron-left"></i> ' + gettext("Previous"),
      'skipLabel': '<i class="fa fa-times"></i> ' + gettext("End tour"),
      'doneLabel': gettext("Done"),
    });
    intro.setOptions({
      'steps': get_steps(),
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

  $(document).on('click', '#vm-details-resources-save, .vm-details-home-edit-name-click, .vm-details-home-edit-description-click, a.operation', function() {
    if(intro)
      intro.exit();
  });
});


function get_steps() {
  // if an activity is running the #ops will be refreshed
  // and the intro will break
  deploy_selector = "#ops";
  save_as_selector = "#ops";
  if(!$('.timeline .activity i').hasClass('fa-spin')) {
    vm_status = $("#vm-details-state").data("status");
    if(vm_status === "PENDING")
      deploy_selector += ' a[class*="operation-deploy"]';
    if(vm_status === "RUNNING" || vm_status === "STOPPED")
      save_as_selector += ' a[class*="operation-save_as_template"]';
  }

  steps = [
    {
      element: document.querySelector("#vm-details-start-template-tour"),
      intro: "<p>" + gettext("Welcome to the template tutorial. In this quick tour, we are going to show you how to do the steps described above.") + "</p>" +
             "<p>" + gettext('For the next tour step press the "Next" button or the right arrow (or "Back" button/left arrow for the previous step).') + "</p>"
    },
    {
      element: document.querySelector('a[href="#home"]'),
      intro: gettext("In this tab you can extend the expiration date of your virtual machine, add tags and modify the name and description."),
    },
    {
      element: document.querySelector('#home_name_and_description'),
      intro: gettext("Please add a meaningful description to the virtual machine. Changing the name is also recommended, however you can choose a new name when saving the template."),
    },
    {
      element: document.querySelector('#home_expiration_and_lease'),
      intro: gettext("You can change the lease to extend the expiration date. This will be the lease of the new template."),
    },
    {
      element: document.querySelector('a[href="#resources"]'),
      intro: gettext("On the resources tab you can edit the CPU/RAM options and add/remove disks if you have required permissions."),
    }
  ];

  if($("#vm-details-resources-save").length) {
    steps.push(
      {
        element: document.querySelector('#vm-details-resources-form'),
        intro: '<p><strong>' + gettext("CPU priority") + ":</strong> " +
                gettext("higher is better") + "</p>" +
                "<p><strong>" + gettext("CPU count") + ":</strong> " +
                gettext("number of CPU cores.") + "</p>" +
                "<p><strong>" + gettext("RAM amount") + ":</strong> " +
                gettext("amount of RAM.") + "</p>",
        position: "top",
      }
    );
  }

  if($(".operation-create_disk").length || $(".operation-download_disk").length) {
    steps.push(
      {
        element: document.querySelector('#vm-details-resources-disk'),
        intro: gettext("You can add empty disks, download new ones and remove existing ones here."),
        position: "top",
      }
    );
  }

  steps.push(
    {
      element: document.querySelector('a[href="#network"]'),
      intro: gettext('You can add new network interfaces or remove existing ones here.'),
    },
    {
      element: document.querySelector(deploy_selector),
      intro: gettext("Deploy the virtual machine."),
    },
    {
      element: document.querySelector("#vm-info-pane"),
      intro: gettext("Use the CIRCLE client or the connection string to connect to the virtual machine."),
    },
    {
      element: document.querySelector("#vm-info-pane"),
      intro: gettext("After you have connected to the virtual machine do your modifications then log off."),
    },
    {
      element: document.querySelector(save_as_selector),
      intro: gettext('Press the "Save as template" button and wait until the activity finishes.'),
    },
    {
      element: document.querySelector(".alert-new-template"),
      intro: gettext("This is the last message, if something is not clear you can do the the tour again."),
    }
  );
  return steps;
}
