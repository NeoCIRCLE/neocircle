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

(function($){
  $.event.special.doubletap = {
    bindType: 'touchend',
    delegateType: 'touchend',

    handle: function(event) {
      var handleObj   = event.handleObj,
          targetData  = jQuery.data(event.target),
          now         = new Date().getTime(),
          delta       = targetData.lastTouch ? now - targetData.lastTouch : 0,
          delay       = delay === null ? 300 : delay;

      if (delta < delay && delta > 30) {
        targetData.lastTouch = null;
        event.type = handleObj.origType;
        ['clientX', 'clientY', 'pageX', 'pageY'].forEach(function(property) {
          event[property] = event.originalEvent.changedTouches[0][property];
        });

        handleObj.handler.apply(this, arguments);
      } else {
        targetData.lastTouch = now;
      }
    }
  };

})(jQuery);

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
    var clickEvent = 0;


    var stackIndexer = 0;
    var stackSize = 0;
    var objectStack = [];
    var undoStack = [];
    var redoStack = [];

    $("#dropContainer").attr('unselectable', 'on').css({
            'user-select': 'none',
            'MozUserSelect': 'none'})
        .on('selectstart', false)
        .on('mousedown', false);


    setServiceStatus = function(status) {
        if (status == "unsaved") {
            $("#serviceStatus").text("Unsaved");
        }
        else {
            $("#serviceStatus").empty();
        }
    };


    addInfo = function(title, info, type, object) {
        $("#informationContainer").empty();

        switch(type){
            case "connection":
                div =
                    '<div class="row">' +
                        '<div class="col-xs-12 text-center">' +
                            '<h4>' + title + '</h4>' +
                        '</div>' +
                    '</div>&nbsp;' +
                    '<div class="row">' +
                        '<div class="col-xs-12">' +
                            '<textarea class="form-control" rows="28" id="infoInput" placeholder="Config data"></textarea>' +
                        '</div>' +
                    '</div>&nbsp;' +
                    '<div class="row">' +
                        '<div class="col-xs-12 text-center">' +
                            '<button id="removeConnection" class="btn btn-info">Remove connection</button>' +
                        '</div>' +
                    '</div>';
                break;
            case "element":
                div =
                    '<div class="row">' +
                        '<div class="col-xs-12 text-center">' +
                            '<h4>' + title + '</h4>' +
                        '</div>' +
                    '</div>&nbsp;' +
                    '<div class="row">' +
                        '<div class="col-xs-12">' +
                            '<textarea class="form-control" rows="24" id="infoInput" placeholder="Config data"></textarea>' +
                        '</div>' +
                    '</div>&nbsp;' +
                    '<div class="row text-center">' +
                        '<label>Endpoints</label>' +
                    '</div>' +
                    '<div class="row">' +
                        '<div class="col-xs-6 text-center">' +
                            '<button id="addEndpoint" class="btn btn-success"><i class="fa fa-plus"></i></button>' +
                        '</div>' +
                        '<div class="col-xs-6 text-center">' +
                            '<button id="removeEndpoint" class="btn btn-danger"><i class="fa fa-minus"></i></button>' +
                        '</div>' +
                    '</div>&nbsp;' +
                    '<div class="row">' +
                        '<div class="col-xs-12 text-center">' +
                            '<button id="removeFromWorkspace" class="btn btn-info">Remove from workspace</button>' +
                        '</div>' +
                    '</div>';
                break;
            case "elementTemplate":
                div =
                    '<div class="row">' +
                        '<div class="col-xs-12 text-center">' +
                            '<h4>' + title + '</h4>' +
                        '</div>' +
                    '</div>&nbsp;' +
                    '<div class="row">' +
                        '<div class="col-xs-12">' +
                            '<textarea class="form-control" rows="28" id="infoInput" placeholder="Config data"></textarea>' +
                        '</div>' +
                    '</div>&nbsp;' +
                    '<div class="row">' +
                        '<div class="col-xs-12 text-center">' +
                            '<button id="addElementToWorkspace" class="btn btn-success">Add to workspace</button>' +
                        '</div>' +
                    '</div>';
                break;
        }

        $("#informationContainer").append(div);

        $("#infoInput").val(info);

        $("#dragPanel").hide();

        $("#informationPanel").show();
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
                addMessage("Twofold connection is forbidden.", "danger");
                return false;
            }
        }
        return true;
    };


    checkCompatibility = function(sourceId, targetId) {
        validTargets = $("#" + sourceId).attr("type").split(',');

        if (jQuery.inArray(targetId.split('_')[1], validTargets) == -1) {
            addMessage("Connecting incompatible elements is forbidden.", "danger");
            return false;
        }
        return true;
    };


    checkSourceTargetEquality = function(connection) {
        if (connection.targetId == connection.sourceId) {
            addMessage("Connecting element to itself is forbidden.", "danger");
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

        if (anchors == 8) return;

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
    };


    removeEndoint = function(element) {
        anchors = element.attr("anchors");

        if (anchors == 4) return;

        i = --anchors;

        while (isConnected(i + "_" + element.attr("id")) && i >= 0) i--;

        if (i == -1) {
            addMessage("Removing anchors is obstructed.", "danger");
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
    };


    removeElement = function(object) {
        jsPlumbInstance.detachAllConnections(object);
        jsPlumbInstance.remove(object.attr("id"));
    };


    scrollContainer = function(direction) {
        dragContainerScroll += direction;

        if (dragContainerScroll == $(".elementTemplate").length - 2) dragContainerScroll--;
        if (dragContainerScroll == -1) dragContainerScroll++;

        $("#dragContainer").scrollTop(
            dragContainerScroll * $("#elementTemplatePanel").height()
        );
    };


    mouseScrollContainer = function(event) {
        var e = window.event || event;
        var delta = Math.max(-1, Math.min(1, (e.wheelDelta || -e.detail)));

        $('body').addClass("noScroll");

        scrollContainer(-delta);

        $('body').removeClass("noScroll");
    };


    jsPlumbInstance.bind("connection", function(info) {
        updateConnections(info.connection);
        info.connection.parameters = "";

        // For right click on a connection.
        $("path").on('doubletap', function() {
            //Todo
        });

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
        $("#informationPanel").hide();
        $("#dragPanel").show();
    });


    jsPlumbInstance.bind("dblclick", function(info) {
        $('.element').removeClass('elementSelected');
        jsPlumbInstance.select().setPaintStyle({strokeStyle:'#9932cc', lineWidth: 8});
        info.setPaintStyle({strokeStyle:"red", lineWidth: 8});
        addInfo($("#" + info.sourceId.split('_')[1]).attr("alt") + ' - ' + $("#" + info.targetId.split('_')[1]).attr("alt"),
            info.parameters,
            "connection",
            info);
    });


    jsPlumbInstance.draggable(jsPlumb.getSelector(".element"), {
        containment: $("#dropContainer")
    });


    $('body').on('click', '.elementTemplate', function() {
        addElement($(this).attr("id"), (++elementIndex) + "_" + $(this).attr("id"), (elementIndex % 21) * 30, 4, "", (elementIndex % 21) * 30);

        undoStack.splice(stackIndexer, 0, removeElement);
        redoStack.splice(stackIndexer, 0, addElement);
        objectStack.splice(stackIndexer, 0, newInstance);
        stackSize++;
        stackIndexer++;
    });


    $('body').on('dblclick doubletap', '.element', function() {
        element = $(this);
        $('.element').removeClass('elementSelected');
        jsPlumbInstance.select().setPaintStyle({strokeStyle:'#9932cc', lineWidth: 8});
        element.addClass("elementSelected");
        addInfo(element.attr("alt"), element.attr("parameters"), "element", element);
        $(document).scrollTop(0);
    });


    $('body').on('contextmenu', '.element', function(event) {
        setServiceStatus("unsaved");
        $("#informationPanel").hide();
        $("#dragPanel").show();

        $('.element').removeClass('elementSelected');
        jsPlumbInstance.select().setPaintStyle({strokeStyle:'#9932cc', lineWidth: 8});

        removeElement($(this));

        undoStack.splice(stackIndexer, 0, addElement);
        redoStack.splice(stackIndexer, 0, removeElement);
        objectStack.splice(stackIndexer, 0, $(this));
        stackSize++;
        stackIndexer++;
    });


    $('body').on('click', '#closeInfoPanel', function() {
        $('#informationPanel').hide();
        $('#dragPanel').show();
        $('.element').removeClass('elementSelected');
        jsPlumbInstance.select().setPaintStyle({strokeStyle:'#9932cc', lineWidth: 8});
    });


    $('body').on('keyUp', '#infoInput', function() {
        setServiceStatus("unsaved");
        newParams = $("#infoInput").val();

        if (type == "connection") object.parameters = newParams;
        if (type == "element") object.attr("parameters", newParams);
    });


    $('body').on('click', '#addEndpoint', function() {
        addEndpoint(object);
        undoStack.splice(stackIndexer, 0, removeEndoint);
        redoStack.splice(stackIndexer, 0, addEndpoint);
        objectStack.splice(stackIndexer, 0, object);
        stackIndexer++;
        stackSize++;
    });


    $('body').on('click', '#removeEndpoint', function() {
        removeEndoint(object);
        undoStack.splice(stackIndexer, 0, addEndpoint);
        redoStack.splice(stackIndexer, 0, removeEndoint);
        objectStack.splice(stackIndexer, 0, object);
        stackIndexer++;
        stackSize++;
    });


    $('body').on('click', '#removeFromWorkspace', function() {
        $('.element').removeClass('elementSelected');
        removeElement(object);

        $("#informationPanel").hide();
        $("#dragPanel").show();

        undoStack.splice(stackIndexer, 0, addElement);
        redoStack.splice(stackIndexer, 0, removeElement);
        objectStack.splice(stackIndexer, 0, object);
        stackSize++;
        stackIndexer++;
    });


    $('body').on('click', '#removeConnection', function() {
        jsPlumbInstance.detach(object);
        $("#informationPanel").hide();
        $("#dragPanel").show();
    });


    $('body').on('click', '#addElementToWorkspace', function() {
        addElement(object.attr("id"), (++elementIndex) + "_" + object.attr("id"), (elementIndex % 21) * 30, 4, "", (elementIndex % 21) * 30);

        undoStack.splice(stackIndexer, 0, removeElement);
        redoStack.splice(stackIndexer, 0, addElement);
        objectStack.splice(stackIndexer, 0, newInstance);
        stackSize++;
        stackIndexer++;
    });


    $('body').on('click', '#clearService', function() {
        jsPlumbInstance.reset();
        $(".element").remove();
        setServiceStatus("unsaved");

        elementIndex = 0;
    });


    $('body').on('click', '#undoMovement', function() {
        if (stackIndexer <= 0) return;
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
        redoStack[stackIndexer++](object);
        clickEvent = 0;
    });


    $('body').on('click', '.elementTemplateInfo', function() {
        id = $(this).attr("element");
        addInfo($("#" + id).attr("alt"), $("#" + id).attr("desc"), "elementTemplate", $("#" + id));
    });


    $('body').on('click', '#serviceName', function() {
        $(this).replaceWith('<input type="text" id="serviceName" class="form-control form-control-sm" style="margin-top: -4px !important; margin-bottom: -4px !important;" value="' + $(this).html() + '" />');
        document.getElementById("serviceName").select();
        setServiceStatus("unsaved");
    });


    $('body').on('click', '#dragContainerScrollUp', function() {
        scrollContainer(-1);
    });


    $('body').on('click', '#dragContainerScrollDown', function() {
        scrollContainer(1);
    });


    $('body').on('click', '#saveService', function() {
        serviceName = $("#serviceName").val() === ''?$("#serviceName").text():$("#serviceName").val();
        connectionSet = [];
        instanceSet = [];

        $.each(elementConnections, function(index) {
            connectionSet.push({
                "sourceId": elementConnections[index].sourceId,
                "sourceEndpoint": elementConnections[index].endpoints[0].getUuid(),
                "targetId": elementConnections[index].targetId,
                "targetEndpoint": elementConnections[index].endpoints[1].getUuid(),
                "parameters": elementConnections[index].parameters});
        });

        $.each($(".element"), function() {
            instanceSet.push({
                "displayId": $(this).prop("id"),
                "posX": Math.floor($(this).position().left),
                "posY": Math.floor($(this).position().top),
                "anchors": $(this).attr("anchors"),
                "parameters": $(this).attr("parameters")});
        });

        $.post("", {
            event: "saveService",
            data: JSON.stringify({
                "serviceName": serviceName,
                "elementConnections": connectionSet,
                "elements": instanceSet})
        }, function(result) {
            addMessage(result.serviceName + " saved successfully.","success");
            setServiceStatus("saved");
        });
    });


    $(window).resize(function() {
        $(".element").each(function() {
            if ($(this).position().left + $(this).width() > $("#dropContainer").position().left + $("#dropContainer").width()) {
                $(this).css("left", $("#dropContainer").position().left + $("#dropContainer").width() - $(this).width() +4);
            }
        });
        jsPlumbInstance.repaintEverything();
    });


    var dragContainer = document.getElementById("dragContainer");

    if (dragContainer.addEventListener) {
        dragContainer.addEventListener("mousewheel", mouseScrollContainer, false);
        dragContainer.addEventListener("DOMMouseScroll", mouseScrollContainer, false);
    } else dragContainer.attachEvent("onmousewheel", mouseScrollContainer);


    $("#searchElementTemplate").keyup(function() {
        $(".elementTemplate").each(function() {
            $(this).parent().parent().hide();
            if ($(this).attr("alt").toLowerCase().indexOf($("#searchElementTemplateInput").val().toLowerCase()) >= 0)
                $(this).parent().parent().show();
        });
    });


    $(document).ready(function() {
        $.post("", {
            event: "loadService"
        }, function(result) {
            if (result === "") return;

            $("#serviceName").text(result.serviceName);

            $.each(result.elements, function(i, element) {
                addElement(element.displayId.split('_')[1],
                    element.displayId,
                    element.posY + "px",
                    element.anchors,
                    element.parameters,
                    element.posX + "px");
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