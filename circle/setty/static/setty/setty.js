/* Settimng up csrf token, touch event and zoom options. */
function getCookie(name) {
  var cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    var cookies = document.cookie.split(';');
    for (var i = 0; i < cookies.length; i++) {
      var cookie = jQuery.trim(cookies[i]);
      if (cookie.substring(0, name.length + 1) == (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

function csrfSafeMethod(method) {
  return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}

var csrftoken = getCookie('csrftoken');

$.ajaxSetup({
  beforeSend: function(xhr, settings) {
    if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
      xhr.setRequestHeader("X-CSRFToken", csrftoken);
    }
  }
});


/* Setty implementation starts here. */

jsPlumb.ready(function() {
  var jsPlumbInstance = jsPlumb.getInstance({
    DragOptions: {
      zIndex: 2000
    },
    EndpointHoverStyle: {
      fillStyle: "green"
    },
    HoverPaintStyle: {
      strokeStyle: "green"
    },
    Container: "dropContainer"
  });
  var jsPlumbEndpoint = {
    endpoint: ["Dot", {
      radius: 10
    }],
    paintStyle: {
      fillStyle: "#9932cc"
    },
    isSource: true,
    isTarget: true,
    deleteEndpointsOnDetach: false,
    zIndex: 20,
    connectorStyle: {
      strokeStyle: "#9932cc",
      lineWidth: 8
    },
    connector: ["Bezier", {
      curviness: 180
    }],
    maxConnections: 1,
    dropOptions: {
      tolerance: "fit"
    }
  };
  var elementConnections = [];
  var elementIndex = 0;
  var dragContainerScroll = 0;
  var workspaceWidth = $("#dropContainer").width();
  var workspaceHeight = $("#dropContainer").height();

  var stackIndexer = 0;
  var stackSize = 0;
  var objectStack = [];
  var undoStack = [];
  var redoStack = [];
  var clickEvent = 0;
  var nextStepConstraint = 0;


  /* Functions. */

  setServiceStatus = function(status) {
    if (status == "unsaved") {
      $("#serviceStatus").text(gettext("Unsaved"));
    } else {
      $("#serviceStatus").empty();
    }
  };

  addInfo = function(title, info, object, type) {
    mainDiv = $("<div>", {
      class: "row",
      html: $("<div>", {
        class: "col-xs-12 text-center",
        html: row = $("<h4>", {
          html: title
        })
      })
    }).add($("<div>", {
      class: "row",
      style: "margin-top: 16px",
      html: $("<div>", {
        class: "col-xs-12 text-center",
        html: row = $("<textarea>", {
          class: "form-control",
          style: "text-align: justify;",
          rows: "18",
          id: "infoInput",
          disabled: !type,
          text: info
        })
      })
    }));
    controlDiv = $("<div>", {
      class: "row",
      style: "margin-top: 16px",
      html: $("<div>", {
        class: "col-xs-3 text-center",
        html: $("<button>", {
          class: "btn btn-success btn-block",
          id: "addEndpoint",
          html: gettext("Add endpoint")
        })
      }).add($("<div>", {
        class: "col-xs-3 text-center",
        html: $("<button>", {
          class: "btn btn-danger btn-block",
          id: "removeEndpoint",
          html: gettext("Delete endpoint")
        })
      })).add($("<div>", {
        class: "col-xs-6 text-center",
        html: $("<button>", {
          class: "btn btn-info btn-block",
          id: "removeElementFromWorkspace",
          html: gettext("Remove from workspace")
        })
      }))
    });
    addElementDiv = $("<div>", {
      class: "row",
      style: "margin-top: 16px",
      html: $("<div>", {
        class: "col-xs-12 text-center",
        html: row = $("<button>", {
          class: "btn btn-success",
          id: "addElementToWorkspace",
          html: gettext("Add to workspace")
        })
      })
    });

    $("#informationContainer").html(type?mainDiv.add(controlDiv):mainDiv.add(addElementDiv));

    $("#changeInformationDialog").modal('show');

    sharedObject = object;
  };

  updateConnections = function(connection, remove) {
    if (!remove) {
      elementConnections.push(connection);
    } else {
      index = -1;
      for (var i = 0; i < elementConnections.length; i++) {
        if (elementConnections[i] == connection) {
          index = i;
          break;
        }
      }
      if (index != -1) {
        elementConnections.splice(index, 1);
      }
    }

    setServiceStatus("unsaved");
  };

  checkDuplicateConnection = function(connection) {
    for (var i = 0; i < elementConnections.length; i++) {
      if (((elementConnections[i].targetId ==
            connection.targetId &&
            elementConnections[i].sourceId ==
            connection.sourceId) ||
          (elementConnections[i].targetId ==
            connection.sourceId &&
            elementConnections[i].sourceId ==
            connection.targetId)) &&
        elementConnections[i] != connection) {
        addMessage(gettext("Twofold connection is forbidden."), "danger");
        return false;
      }
    }
    return true;
  };

  checkCompatibility = function(sourceId, targetId) {
    validTargets = $("#" + sourceId).attr("type").split(',');

    if (jQuery.inArray(targetId.split('_')[1], validTargets) == -1) {
      addMessage(gettext("Connecting incompatible elements is forbidden."), "danger");
      return false;
    }
    return true;
  };

  checkSourceTargetEquality = function(connection) {
    if (connection.targetId == connection.sourceId) {
      addMessage(gettext("Connecting element to itself is forbidden."), "danger");
      return false;
    }
    return true;
  };

  getAnchorCoordinate = function(rate) {
    x = Math.cos(2.0 * Math.PI * rate) / 2;
    y = Math.sin(2.0 * Math.PI * rate) / 2;
    dx = 0;
    dy = 0;

    if (rate < 0.125) {
      x = 0.5;
      dx = 1;
    } else if (rate > 0.125 && rate < 0.375) {
      y = -0.5;
      dy = -1;
    } else if (rate > 0.375 && rate < 0.625) {
      x = -0.5;
      dx = -1;
    } else if (rate > 0.625 && rate < 0.875) {
      y = 0.5;
      dy = 1;
    } else if (rate > 0.875) {
      x = -0.5;
      dx = -1;
    } else {
      x = Math.sqrt(2) * Math.cos(2 * Math.PI *
        rate) / 2;
      y = Math.sqrt(2) * Math.sin(2 * Math.PI *
        rate) / 2;

      dx = Math.round(2 * x);
    }
    return [y + 0.5, -x + 0.5, dy, -dx];
  };

  isConnected = function(anchorId) {
    returnValue = false;
    $.each(elementConnections, function(index) {
      if (elementConnections[index].endpoints[0].getUuid() == anchorId ||
        elementConnections[index].endpoints[1].getUuid() == anchorId) {
        returnValue = true;
        return;
      }
    });
    return returnValue;
  };

  elementIsConnected = function(element) {
    anchors = element.attr("anchors");
    id = element.attr("id");

    for (i = 0; i < anchors; i++) {
      if (isConnected(i + "_" + id)) {
        return true;
      }
    }

    return false;
  };

  getConnectionparamAndAnchor = function(anchorId) {
    parameters = "";
    otherAnchor = "";

    $.each(elementConnections, function(index) {
      if (elementConnections[index].endpoints[0].getUuid() == anchorId) {
        parameters = elementConnections[index].parameters;
        otherAnchor = elementConnections[index].endpoints[1].getUuid();
        return;
      }

      if (elementConnections[index].endpoints[1].getUuid() == anchorId) {
        parameters = elementConnections[index].parameters;
        otherAnchor = elementConnections[index].endpoints[0].getUuid();
        return;
      }
    });

    return [otherAnchor, parameters];
  };

  addEndpoint = function(element) {
    anchors = element.attr("anchors");

    if (anchors == 8) return 1;

    anchors++;

    jsPlumbInstance.addEndpoint(document.getElementById(element.attr("id")), {
        uuid: (anchors - 1) + "_" + element.attr("id")
      },
      jsPlumbEndpoint);

    for (i = 0; i < anchors; i++) {
      jsPlumbInstance.getEndpoint(i + "_" + element.attr("id")).setAnchor(getAnchorCoordinate(i / (anchors)));
    }

    element.attr("anchors", anchors);

    jsPlumbInstance.repaintEverything();
    
    return 0;
  };

  removeEndoint = function(element) {
    anchors = element.attr("anchors");

    if (anchors == 4) return 1;

    i = --anchors;

    while (isConnected(i + "_" + element.attr("id")) && i >= 0) i--;

    if (i == -1) {
      addMessage(gettext("Removing anchors is obstructed."), "danger");
      return;
    } else if (i == anchors) {
      jsPlumbInstance.deleteEndpoint(jsPlumbInstance.getEndpoint(anchors + "_" + element.attr("id")));
    } else {
      newId = i + "_" + element.attr("id");
      oldId = anchors + "_" + element.attr("id");

      data = getConnectionparamAndAnchor(oldId);
      data.splice(0, 0, newId);

      jsPlumbInstance.deleteEndpoint(jsPlumbInstance.getEndpoint(oldId));

      connectEndpoints(data);
    }

    for (i = 0; i < anchors; i++) jsPlumbInstance.getEndpoint(
      i + "_" + element.attr("id")).setAnchor(getAnchorCoordinate(i / (anchors)));

    element.attr("anchors", anchors);

    jsPlumbInstance.repaintEverything();
    
    return 0;
  };

  connectEndpoints = function(data) {
    connectionObject =
      jsPlumbInstance.connect({
        uuids: [data[0], data[1]]
      });

    connectionObject.parameters = data[2];

    setServiceStatus("unsaved");
  };

  disconnectEndpoints = function(data) {
    for (var i = 0; i < elementConnections.length; i++) {
      if (elementConnections[i].endpoints[0].getUuid() == data[0] &&
        elementConnections[i].endpoints[1].getUuid() == data[1]) {
        jsPlumbInstance.detach(elementConnections[i]);
        return;
      }
    }
    return;
  };

  addElement = function(idOrInstance, newId, newPositionY, endpoints, parameters, newPositionX) {
    newInstance = "";

    if (typeof idOrInstance != "string") {
      newInstance = idOrInstance;
      endpoints = newInstance.attr("anchors");
      newInstance.attr("anchors", 0);
    } else {
      newInstance = $('#' + idOrInstance)
        .clone()
        .prop("id", newId)
        .prop("title", "Right click to delete")
        .removeClass()
        .addClass("element")
        .attr("anchors", 0)
        .attr("parameters", parameters)
        .css("top", newPositionY)
        .css("left", newPositionX);
    }

    $("#dropContainer").append(newInstance);

    for (i = 0; i <= endpoints; i++) {
      addEndpoint(newInstance);
    }

    jsPlumbInstance.draggable(jsPlumb.getSelector(".element"), {
      containment: $("#dropContainer")
    });

    setServiceStatus("unsaved");

    jsPlumbInstance.repaintEverything();

    return newInstance;
  };

  removeElement = function(object) {
    jsPlumbInstance.detachAllConnections(object);
    jsPlumbInstance.remove(object.attr("id"));
  };


  /* Registering events using JsPlumb. */

  jsPlumbInstance.bind("connection", function(info) {
    updateConnections(info.connection);
    info.connection.parameters = "";

    if (clickEvent === 0) {
      undoStack.splice(stackIndexer, 0, disconnectEndpoints);
      redoStack.splice(stackIndexer, 0, connectEndpoints);
      connectionArray = [];
      connectionArray.push(info.connection.endpoints[0].getUuid(),
        info.connection.endpoints[1].getUuid(),
        info.connection.parameters);
      objectStack.splice(stackIndexer, 0, connectionArray);
      stackIndexer++;
      stackSize++;
    }
  });

  jsPlumbInstance.bind("beforeDrop", function(info) {
    return checkDuplicateConnection(info.connection) &&
      checkSourceTargetEquality(info.connection) &&
      checkCompatibility(info.connection.sourceId, info.connection.targetId);
  });

  jsPlumbInstance.bind("connectionDetached", function(info) {
    updateConnections(info.connection, true);

    if (clickEvent === 0) {
      undoStack.splice(stackIndexer, 0, connectEndpoints);
      redoStack.splice(stackIndexer, 0, disconnectEndpoints);
      connectionArray = [];
      connectionArray.push(info.connection.endpoints[0].getUuid(),
        info.connection.endpoints[1].getUuid(),
        info.connection.parameters);
      objectStack.splice(stackIndexer, 0, connectionArray);
      stackIndexer++;
      stackSize++;
    }
  });

  jsPlumbInstance.bind("connectionMoved", function(info) {
    updateConnections(info.connection, true);
  });

  jsPlumbInstance.bind("contextmenu", function(info) {
    jsPlumbInstance.detach(info);
  });

  jsPlumbInstance.draggable(jsPlumb.getSelector(".element"), {
    containment: $("#dropContainer")
  });


  /* Registering events using JQuery. */

  $('body').on('click', '.elementTemplate', function() {
    addElement($(this).attr("id"),
      (++elementIndex) + "_" + $(this).attr("id"),
      (elementIndex % 21) * 30, 4, "",
      (elementIndex % 21) * 30);

    undoStack.splice(stackIndexer, 0, removeElement);
    redoStack.splice(stackIndexer, 0, addElement);
    objectStack.splice(stackIndexer, 0, newInstance);
    stackSize++;
    stackIndexer++;
  });

  $('body').on('dblclick', '.element', function() {
    element = $(this);
    element.addClass("elementSelected");
    addInfo(element.attr("alt"),
      element.attr("parameters"),
      element, 1);
    $(document).scrollTop(0);
  });

  $('body').on('contextmenu', '.element', function(event) {
    setServiceStatus("unsaved");
    removeElement($(this));

    undoStack.splice(stackIndexer, 0, addElement);
    redoStack.splice(stackIndexer, 0, removeElement);
    objectStack.splice(stackIndexer, 0, $(this));

    nextStepConstraint = 0;
    stackSize++;
    stackIndexer++;
  });

  $('body').on('keyup', '#infoInput', function() {
    setServiceStatus("unsaved");
    newParams = $("#infoInput").val();

    sharedObject.attr("parameters", newParams);
  });

  $('body').on('click', '#addEndpoint', function() {
    setServiceStatus("unsaved");
    if(addEndpoint(sharedObject)) return;
    undoStack.splice(stackIndexer, 0, removeEndoint);
    redoStack.splice(stackIndexer, 0, addEndpoint);
    objectStack.splice(stackIndexer, 0, sharedObject);
    stackIndexer++;
    stackSize++;
  });

  $('body').on('click', '#removeEndpoint', function() {
    setServiceStatus("unsaved");
    if(removeEndoint(sharedObject)) return;
    undoStack.splice(stackIndexer, 0, addEndpoint);
    redoStack.splice(stackIndexer, 0, removeEndoint);
    objectStack.splice(stackIndexer, 0, sharedObject);
    stackIndexer++;
    stackSize++;
  });

  $('body').on('click', '#removeElementFromWorkspace', function() {
    setServiceStatus("unsaved");
    removeElement(sharedObject);

    undoStack.splice(stackIndexer, 0, addElement);
    redoStack.splice(stackIndexer, 0, removeElement);
    objectStack.splice(stackIndexer, 0, sharedObject);
    stackSize++;
    stackIndexer++;

    $("#changeInformationDialog").modal('hide');
  });

  $('body').on('click', '#removeConnection', function() {
    jsPlumbInstance.detach(sharedObject);
  });

  $('body').on('click', '#addElementToWorkspace', function() {
    newInstance = addElement(sharedObject.attr("id"),
      (++elementIndex) + "_" + sharedObject.attr("id"),
      (elementIndex % 21) * 30, 4, "",
      (elementIndex % 21) * 30);

    undoStack.splice(stackIndexer, 0, removeElement);
    redoStack.splice(stackIndexer, 0, addElement);
    objectStack.splice(stackIndexer, 0, newInstance);
    stackSize++;
    stackIndexer++;
  });

  $('body').on('click', '#clearService', function() {
    //Todo
    setServiceStatus("unsaved");

    elementIndex = 0;
  });

  $('body').on('click', '#undoMovement', function() {
    if (stackIndexer < 1) return;
    stackIndexer--;
    clickEvent = 1;
    object = objectStack[stackIndexer];
    undoStack[stackIndexer](object);
    clickEvent = 0;
  });

  $('body').on('click', '#redoMovement', function() {
    if (stackIndexer >= stackSize) return;
    clickEvent = 1;
    object = objectStack[stackIndexer];
    redoStack[stackIndexer](object);
    stackIndexer++;
    clickEvent = 0;
  });

  $('body').on('click', '#addMachineDialog', function() {
    // Here comes the ajax post of getting machines
  });

  $('body').on('click', '.elementTemplateInfo', function() {
    id = $(this).attr("element");
    addInfo($("#" + id).attr("alt"), $("#" + id).attr("desc"), $("#" + id), 0);
  });

  $('body').on('click', '#serviceName', function() {
    $('#serviceName').hide();
    $("#serviceNameEdit").css("display", "inline").val($(this).text()).select();
    $("#serviceNameSave").css("display", "inline");
    setServiceStatus("unsaved");
  });

  $('body').on('click', '#serviceNameSave', function() {
    $('#serviceNameEdit').hide();
    $(this).hide();
    $("#serviceName").show().text($('#serviceNameEdit').val());
  });

  $('body').on('click', '#dragContainerScrollUp', function() {
    scrollContainer(-1);
  });

  $('body').on('click', '#dragContainerScrollDown', function() {
    scrollContainer(1);
  });

  $('body').on('hide.bs.modal', '#changeInformationDialog', function() {
    $('.element').removeClass('elementSelected');
  });

  $('body').on('keyup', '#searchElementTemplate', function() {
    $(".elementTemplate").each(function() {
      $(this).parent().parent().hide();
      if ($(this).attr("alt").toLowerCase().indexOf($("#searchElementTemplateInput").val().toLowerCase()) >= 0)
        $(this).parent().parent().show();
    });
  });

  $('body').on('mousewheel DOMMouseScroll onmousewheel', function(event) {
    var e = window.event || event;
    var delta = Math.max(-1, Math.min(1, (e.wheelDelta || -e.detail)));

    $('body').addClass("noScroll");

    dragContainerScroll -= delta;

    if (dragContainerScroll == $(".elementTemplate").length - 2) dragContainerScroll--;
    if (dragContainerScroll == -1) dragContainerScroll++;

    $("#dragContainer").scrollTop(
      dragContainerScroll * $("#elementTemplatePanel").height()
    );

    $('body').removeClass("noScroll");
  });

  $(document).on('keydown', function(e) {
    var eventObject = window.event ? event : e;

    // Undo (CTRL + Z)
    if (eventObject.keyCode == 90 && eventObject.ctrlKey) {
      eventObject.preventDefault();
      $('#undoMovement').click();
    }

    // Redo (CTRL + Y)
    if (eventObject.keyCode == 89 && eventObject.ctrlKey) {
      eventObject.preventDefault();
      $('#redoMovement').click();
    }

    // Add element (CTRL + A)
    if (eventObject.keyCode == 65 && eventObject.ctrlKey) {
      eventObject.preventDefault();
      $('#showAddElementDialog').click();
    }

    // Clean (CTRL + C)
    if (eventObject.keyCode == 67 && eventObject.ctrlKey) {
      eventObject.preventDefault();
      $('#clearService').click();
    }

    // Save (CTRL + S)
    if (eventObject.keyCode == 83 && eventObject.ctrlKey) {
      eventObject.preventDefault();
      $('#saveService').click();
    }

    // Delete (CTRL + D)
    if (eventObject.keyCode == 68 && eventObject.ctrlKey) {
      eventObject.preventDefault();
      $('#deleteService').click();
    }

    // Close dialog (ESC)
    if (eventObject.keyCode == 27) {
      eventObject.preventDefault();
      $("#changeInformationDialog").modal('hide');
      $("#addElementDialog").modal('hide');
    }
  });

  $(window).on('resize', function() {
    $(".element").each(function() {
      rate = ($(this).position().left) / workspaceWidth;
      left = rate * ($("#dropContainer").width());
      $(this).css("left", left);
    });
    workspaceWidth = $("#dropContainer").width();
    jsPlumbInstance.repaintEverything();
  });


  /* Registering events concerning persistence. */

  $('body').on('click', '#saveService', function() {
    serviceName = $("#serviceName").text();
    connectionSet = [];
    instanceSet = [];

    $.each(elementConnections, function(index) {
      connectionSet.push({
        "sourceId": elementConnections[index].sourceId,
        "sourceEndpoint": elementConnections[index].endpoints[0].getUuid(),
        "targetId": elementConnections[index].targetId,
        "targetEndpoint": elementConnections[index].endpoints[1].getUuid(),
        "parameters": elementConnections[index].parameters
      });
    });

    $.each($(".element"), function() {
      instanceSet.push({
        "displayId": $(this).prop("id"),
        "positionLeft": $(this).position().left / workspaceWidth,
        "positionTop": $(this).position().top / workspaceHeight,
        "anchorNumber": $(this).attr("anchors"),
        "parameters": $(this).attr("parameters")
      });
    });

    $.post("", {
      event: "saveService",
      data: JSON.stringify({
        "serviceName": serviceName,
        "elementConnections": connectionSet,
        "elements": instanceSet
      })
    }, function(result) {
      addMessage(result.serviceName + gettext(" saved successfully."), "success");
      setServiceStatus("saved");
    });
  });

  $(document).ready(function() {
    if (!$("#dropContainer").length) return; // Protection for not posting sites that differ from setty sites.
    $.post("", {
      event: "loadService"
    }, function(result) {
      $("#serviceName").text(result.serviceName);

      $.each(result.elements, function(i, element) {
        addElement(element.displayId.split('_')[1],
          element.displayId,
          (element.positionTop * workspaceHeight) + "px",
          element.anchorNumber,
          element.parameters,
          (element.positionLeft * workspaceWidth) + "px");
        if (elementIndex < element.displayId.split('_')[0])
          elementIndex = element.displayId.split('_')[0];
        elementIndex++;
      });

      clickEvent = 1;
      $.each(result.elementConnections,
        function(i, connection) {
          connectEndpoints([connection.sourceEndpoint, connection.targetEndpoint, connection.parameters]);
        });
      clickEvent = 0;
      setServiceStatus("saved");
    });
  });
});
