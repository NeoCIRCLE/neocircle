jsPlumb.ready(function(){
    /**
     * Global variables.
     */
    var jsPlumbInstance = jsPlumb.getInstance({
        DragOptions: {
            cursor: 'pointer',
            zIndex: 2000
        },
        EndpointHoverStyle: {
            fillStyle: "green"
        },
        HoverPaintStyle: {
            strokeStyle: "red"
        },
        Container: "dropContainer"
    });
    var jsPlumbEndpoint = {
        endpoint: ["Dot", {
            radius: 10,
        }],
        paintStyle: {
            fillStyle: "#9932cc",
        },
        isSource: true,
        isTarget: true,
        deleteEndpointsOnDetach: false,
        zIndex: 20,
        connectorStyle: {
            strokeStyle: "#9932cc",
            lineWidth: 8,
        },
        connector: ["Bezier", {
            curviness: 180,
        }],
        maxConnections: 1,
        dropOptions: {
            tolerance: "fit",
        },
    };
    var elementConnections = [];
    var elementIndex = 0;
    var dragContainerScroll = 0;
    var saveWarning = 0;


    /**
     * Function for updating saved status.
     */
    setServiceStatus = function(status){
        if(status == "unsaved" && $("#unsavedDiv").length < 1){
            $("#serviceName").parent().append('<h3 id="unsavedDiv"> (unsaved)</h3>');
        }
        if(status == "saved"){
            $("#unsavedDiv").remove();
        }
    };


    /**
     * Function for displaying information panel content.
     */
    addInfo = function(title, info, type, element){
        div = '<div class="row"><div class="col-xs-12 text-center"><h3>' + title + '</h3></div></div>&nbsp;<div class="row"><div class="col-xs-12">' + '<textarea class="form-control" rows="30" id="infoInput"' + 'placeholder="Config data"' + (type=="info"?'readonly':'') + '>' + '</textarea></div></div>';

        if(type=="element")
            div += '&nbsp;<div class="row text-center"><label>Endpoints</label></div><div class="row">' + '<div class="col-xs-6 text-center">' + '<button id="addEndpoint" class="btn btn-success">+</button></div>' + '<div class="col-xs-6 text-center">' + '<button id="removeEndpoint" class="btn btn-danger">-</button></div></div>';

        $("#informationContainer").empty().append(div);
        
        $("#infoInput").val(info).keyup(function(){
            setServiceStatus("unsaved");
            newParams = $("#infoInput").val();

            if(type=="connection") element.parameters = newParams;
            if(type=="element") element.attr("parameters", newParams);
        });

        $("#addEndpoint").click(function(){
            addEndpoint(element);
        });

        $("#removeEndpoint").click(function(){
            removeEndoint(element);
        });
    };


    /**
     * Function for updating connection array whether an event was fired.
     */
    updateConnections = function(connection, remove){
        setServiceStatus("unsaved");
        if (!remove)
            elementConnections.push(connection);
        else {
            index = -1;
            for (var i = 0; i < elementConnections.length; i++) {
                if (elementConnections[i] == connection) {
                    index = i;
                    break;
                }
            }
            if (index != -1)
                elementConnections.splice(index, 1);
        }
    };


    /**
     * Function for checking and ignoring duplicate connections.
     */
    checkDuplicateConnection = function(connection){
        for (var i = 0; i < elementConnections.length; i++) {
            if ((elementConnections[i].targetId == connection.targetId && elementConnections[i].sourceId == connection.sourceId) ||
                (elementConnections[i].targetId == connection.sourceId && elementConnections[i].sourceId == connection.targetId)) {
                addMessage("Duplicate connection.", "danger");
                return false;
            }
        }
        return true;
    };


    /**
     * Function for checking element compatibility.
     */
    checkCompatibility = function(sourceId, targetId){
        validTargets = $("#" + sourceId).attr("type").split(',');

        if (jQuery.inArray(targetId.split('_')[1], validTargets) == -1) {
            addMessage("Elements are incompatible.", "danger");
            return false;
        }
        return true;
    };


    /**
     * Function for checking source and target equality.
     */
    checkSourceTargetEquality = function(connection){
        if (connection.targetId == connection.sourceId) {
            addMessage("Source element is the same as target element.", "danger");
            return false;
        }
        return true;
    };


    /**
     * Function for determining anchor positions for an element.
     */
    getAnchorCoordinate = function(rate){
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
            x = Math.sqrt(2) * Math.cos(2 * Math.PI * rate) / 2;
            y = Math.sqrt(2) * Math.sin(2 * Math.PI * rate) / 2;

            dx = Math.round(2 * x);
        }
        return [y + 0.5, -x + 0.5, dy, -dx];
    };


    /**
     * Check whether an anchor is connected.
     */
    isConnected = function(anchorId){
        returnValue = false;
        $.each(elementConnections, function(index) {
            if(elementConnections[index].endpoints[0].getUuid()==anchorId ||
               elementConnections[index].endpoints[1].getUuid()==anchorId){
                returnValue = true;
                return;
            }
        });
        return returnValue;
    };
    
    /**
     * Get connection parameters and other connected anchor concerning an anchor coming from parameters.
     */
    getConnectionparamAndAnchor = function(anchorId){
        parameters = "";
        otherAnchor = "";

        $.each(elementConnections, function(index) {
            if(elementConnections[index].endpoints[0].getUuid()==anchorId)
            {
                parameters = elementConnections[index];
                otherAnchor = elementConnections[index].endpoints[1].getUuid();
                return;
            }

            if(elementConnections[index].endpoints[1].getUuid()==anchorId)
            {
                parameters = elementConnections[index].parameters;
                otherAnchor = elementConnections[index].endpoints[0].getUuid();
                return;
            }
        });
        return [parameters, otherAnchor];
    };
    
    
    /**
     * Function to add new element to service.
     */
    addEndpoint = function(element){
        anchors = element.attr("anchors");

        if(anchors==8) return;

        anchors++;

        jsPlumbInstance.addEndpoint(document.getElementById(element.attr("id")), {
            anchor: getAnchorCoordinate((anchors-1) / anchors),
            uuid: (anchors-1) + "_" + element.attr("id")
        },
        jsPlumbEndpoint);

        for (i = 0; i < anchors; i++) jsPlumbInstance.getEndpoint(i + "_" + element.attr("id")).setAnchor(getAnchorCoordinate(i / (anchors)));

        element.attr("anchors", anchors);
        
        jsPlumbInstance.repaintEverything();
    };

    /**
     * Function for removing an endpoint of an element.
     */
    removeEndoint = function(element){
        anchors = element.attr("anchors");
        
        if(anchors==4) return;
        
        i = anchors-1;
        anchors--;
        
        while(isConnected(i + "_" + element.attr("id")) && i>=0){
            i--;
        }
        
        if(i==-1){
            addMessage("All the anchors are connected so that removing any is forbidden.", "danger");
            return;
        }
        else if(i==anchors){
            jsPlumbInstance.deleteEndpoint(jsPlumbInstance.getEndpoint(anchors + "_" + element.attr("id")));
        }
        else{
            newId = i + "_" + element.attr("id");
            oldId = anchors + "_" + element.attr("id");

            data = getConnectionparamAndAnchor(oldId);
            
            jsPlumbInstance.deleteEndpoint(jsPlumbInstance.getEndpoint(oldId));

            connectionObject = jsPlumbInstance.connect({
                    uuids: [newId, data[1]]
            });
            connectionObject.parameters = data[0];
        }
        
        for (i=0;i<anchors;i++) jsPlumbInstance.getEndpoint(i + "_" + element.attr("id")).setAnchor(getAnchorCoordinate(i / (anchors)));

        element.attr("anchors", anchors);

        jsPlumbInstance.repaintEverything();
    };
    

    /**
     * Function for managing instantiation of new elements based on their templates.
     */
    addElement = function(templateId, newId, newPositionY, endpoints, parameters, newPositionX){
        newInstance = $('#' + templateId)
            .clone()
            .prop("id", newId)
            .prop("title", "Right click to delete")
            .removeClass()
            .addClass("element")
            .attr("anchors", 0)
            .attr("parameters", parameters)
            .css("top", newPositionY)
            .css("left", newPositionX);

        $("#dropContainer").append(newInstance);

        for (i = 0; i <= endpoints; i++) {
            addEndpoint(newInstance);
        }

        jsPlumbInstance.draggable(jsPlumb.getSelector(".element"), {
            containment: $("#dropContainer")
        });

        newInstance.mousedown(function(e){
            if(e.button === 0){
                element = $(this);
                addInfo(element.attr("alt"), element.attr("parameters"), "element", element);
                return false;
            }
            if(e.button == 2){
                setServiceStatus("unsaved");
                $("#informationContainer").empty();
                jsPlumbInstance.remove($(this).prop("id"));
                return false;
            }
            return true;
        });

        setServiceStatus("unsaved");
        
        jsPlumbInstance.repaintEverything();
    };


    /**
     * Handling events on workspace.
     */
    jsPlumbInstance.bind("connection", function(info){
        updateConnections(info.connection);
        info.connection.parameters = "";
    });
    jsPlumbInstance.bind("beforeDrop", function(info){
        return checkDuplicateConnection(info.connection) &&
            checkSourceTargetEquality(info.connection) &&
            checkCompatibility(info.connection.sourceId, info.connection.targetId);
    });
    jsPlumbInstance.bind("connectionDetached", function(info){
        updateConnections(info.connection, true);
    });
    jsPlumbInstance.bind("connectionMoved", function(info){
        updateConnections(info.connection, true);
    });
    jsPlumbInstance.bind("contextmenu", function(info){
        jsPlumbInstance.detach(info);
        $("#informationContainer").empty();
    });
    jsPlumbInstance.bind("click", function(info){
        addInfo($("#"+info.sourceId.split('_')[1]).attr("alt") + ' - ' + $("#"+info.targetId.split('_')[1]).attr("alt"),
                info.parameters,
                "connection",
                info);
    });
    jsPlumbInstance.draggable(jsPlumb.getSelector(".element"), {
        containment: $("#dropContainer")
    });


    /**
     * Handling click event on elements.
     */
    $(".elementTemplate").click(function(){
        addElement($(this).prop("id"),
            (++elementIndex) + "_" + $(this).prop("id"),
            $(this).position().top,
            4,
            "");
    });


    /**
     * Handling mouse enter event on elementTemplate for diplaying info.
     */
    $(".elementTemplate").mouseenter(function(){
        addInfo($(this).attr("alt"), $(this).attr("desc"), "info");
    });


    /**
     * Handling click event on clear button.
     */
    $("#clearService").click(function(e){
        jsPlumbInstance.detachEveryConnection()
                       .deleteEveryEndpoint();
        $(".element").remove();
        setServiceStatus("unsaved");
        
        jsPlumbInstance.repaintEverything();
        
        elementIndex = 0;
    });

    
    /**
     * Handling status change in case of renaming service.
     */
    $("#serviceName").keydown(function(){
        setServiceStatus("unsaved");
    });

    /**
     * Handling click event on save button.
     */
    $("#saveService").click(function(){
        serviceName = $("#serviceName").text();
        connectionSet = [];
        instanceSet = [];

        $.each(elementConnections, function(index){
            connectionSet.push({
                "sourceId": elementConnections[index].sourceId,
                "sourceEndpoint": elementConnections[index].endpoints[0].getUuid(),
                "targetId": elementConnections[index].targetId,
                "targetEndpoint": elementConnections[index].endpoints[1].getUuid(),
                "parameters": elementConnections[index].parameters
            });
        });

        $.each($(".element"), function(index){
            instanceSet.push({
                "displayId": $(this).prop("id"),
                "posX": Math.floor($(this).position().left),
                "posY": Math.floor($(this).position().top),
                "anchors": $(this).attr("anchors"),
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
        }, function(resultValue) {
            if (window.location.href.indexOf("/create") >= 0) {
                window.location = "../" + resultValue;
            } else {
                addMessage("Saved successfully.", "success");
                setServiceStatus("saved");
            }
        });
    });


    /**
     * Handling window resize event for preventing elements against overflow.
     */
    $(window).resize(function(){
        $(".element").each(function(){
            if ($(this).position().left + $(this).width() > $("#dropContainer").position().left + $("#dropContainer").width()) {
                $(this).css("left", $("#dropContainer").position().left + $("#dropContainer").width() - $(this).width() + 4);
            }
        });
        jsPlumbInstance.repaintEverything();
    });


    /**
     * Handling click events on scroll buttons.
     */
    $("#dragContainerScrollUp").click(function(){
        if (dragContainerScroll > 0) dragContainerScroll -= 1;
        $("#dragContainer").scrollTop(dragContainerScroll * $("#elementTemplatePanel").height());
    });

    $("#dragContainerScrollDown").click(function(){
        if (dragContainerScroll < $(".elementTemplate").length - 3) dragContainerScroll += 1;
        $("#dragContainer").scrollTop(dragContainerScroll * $("#elementTemplatePanel").height());
    });


    /**
     * Handling search feature.
     */
    $("#searchElementTemplate").keyup(function(){
        $(".elementTemplate").each(function(){
            $(this).parent().parent().hide();
            if ($(this).attr("alt").toLowerCase()
                .indexOf($("#searchElementTemplateInput")
                .val().toLowerCase()) >= 0) {
                $(this).parent().parent().show();
            }
        });
    });


    /**
     * Handling page load event.
     */
    $(document).ready(function(){
        $.post("", {
            event: "loadService"
        }, function(resultValue) {
            if(resultValue === "") return;

            result = jQuery.parseJSON(resultValue);
            $("#serviceName").text(result.serviceName);

            $.each(result.elements, function(i, element) {
                addElement(element.displayId.split('_')[1],
                    element.displayId,
                    element.posY + "px",
                    element.anchors,
                    element.parameters,
                    element.posX + "px");
                if (elementIndex < element.displayId.split('_')[0]) {
                    elementIndex = element.displayId.split('_')[0];
                }
                elementIndex++;
            });

            $.each(result.elementConnections, function(i, connection) {
                connectionObject = jsPlumbInstance.connect({
                    uuids: [connection.sourceEndpoint, connection.targetEndpoint]
                });
                connectionObject.parameters = connection.parameters;
            });
            setServiceStatus("saved");
        });
    });
});