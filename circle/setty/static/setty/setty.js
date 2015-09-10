(function() {
    /**
     * Section to store base data.
     */
    var elementConnections = [];
    var elementIndex = 0;
    var dragContainerScroll = 0;
    var clickedConnection;


    /***
     * Function for updating connection array in whether an event was fired.
     */
    updateConnections = function(conn, remove) {
        if (!remove)
            elementConnections.push(conn);
        else {
            var idx = -1;
            for (var i = 0; i < elementConnections.length; i++) {
                if (elementConnections[i] == conn) {
                    idx = i;
                    break;
                }
            }
            if (idx != -1)
                elementConnections.splice(idx, 1);
        }
    };


    /***
     * Function for checking duplicate connections.
     */
    checkDuplicateConnection = function(connection) {
        for (var i = 0; i < elementConnections.length; i++) {
            if ((elementConnections[i].targetId == connection.targetId && elementConnections[i].sourceId == connection.sourceId) ||
                (elementConnections[i].targetId == connection.sourceId && elementConnections[i].sourceId == connection.targetId)) {
                addMessage("Duplicate connection.", "danger");
                return false;
            }
        }

        return true;
    };


    /***
     * Function for checking element compatibility.
     */
    checkCompatibility = function(sourceId, targetId) {
        var validTargets = $("#" + sourceId).attr("type").split(',');

        if (jQuery.inArray(targetId.split('_')[1], validTargets) == -1) {
            addMessage("Elements are incompatible.", "danger");
            return false;
        }

        return true;
    };


    /***
     * Function for checking source and target element equality.
     */
    checkSourceTargetEquality = function(connection) {
        if (connection.targetId == connection.sourceId) {
            addMessage("Source element is the same as target element.", "danger");
            return false;
        }

        return true;
    };


    /***
     * Function for determining anchor positions for an element.
     */
    getAnchorCoordinate = function(anchor, anchorNum) {
        var rate = anchor / anchorNum;
        var x = Math.cos(2.0 * Math.PI * rate) / 2;
        var y = Math.sin(2.0 * Math.PI * rate) / 2;

        if (rate < 0.125) {
            x = 0.5;
        } else if (rate > 0.125 && rate < 0.375) {
            y = -0.5;
        } else if (rate > 0.375 && rate < 0.625) {
            x = -0.5;
        } else if (rate > 0.625 && rate < 0.875) {
            y = 0.5;
        } else if (rate > 0.875) {
            x = -0.5;
        } else {
            x = Math.sqrt(2) * Math.cos(2 * Math.PI * rate) / 2;
            y = Math.sqrt(2) * Math.sin(2 * Math.PI * rate) / 2;
        }
        return [y + 0.5, -x + 0.5];
    };


    /***
     * Function for managing instantiation of new elements based on their templates.
     */
    addNewElement = function(instance, endpointType, templateId, newId, newPositionY, endpoints, parameters, newPositionX) {
        var newInstance = $('#' + templateId).clone()
            .prop("id", newId)
            .prop("title", "Right click to delete")
            .removeClass();

        if (newPositionY != "")
            newInstance.css("top", newPositionY);

        if (newPositionX != "")
            newInstance.css("left", newPositionX);

        newInstance.addClass("element");
        newInstance.attr("anchors", endpoints);
        $("#dropContainer").append(newInstance);

        for (i = 0; i < endpoints; i++) {
            var coordinates = getAnchorCoordinate(i, endpoints);

            instance.addEndpoint(document.getElementById(newId), {
                anchor: [coordinates[0], coordinates[1], 0, 0],
                uuid: i + "_" + newId,
            }, endpointType);
        }

        instance.draggable(jsPlumb.getSelector(".element"), {
            containment: $("#dropContainer")
        });

        $(".element").mousedown(function(e) {
            if (e.button == 2) {
                instance.remove($(this).prop("id"));
                return false;
            }
            return true;
        });
    };


    /**
     * The main loop. This main function controls everything based on JQuery.
     */
    jsPlumb.ready(function() {
        var instance = jsPlumb.getInstance({
            DragOptions: {
                cursor: 'pointer',
                zIndex: 2000,
            },
            EndpointHoverStyle: {
                fillStyle: "green",
            },
            HoverPaintStyle: {
                strokeStyle: "red",
            },
            EndpointStyle: {
                width: 20,
                height: 20,
            },
            Endpoint: "Rectangle",
            Anchors: ["TopCenter", "TopCenter"],
            Container: "dropContainer"
        });


        /**
         * Loop for handling events.
         */
        instance.doWhileSuspended(function() {
            instance.bind("connection", function(info) {
                updateConnections(info.connection);
                info.connection.parameters = "";
            });
            instance.bind("beforeDrop", function(info) {
                return checkDuplicateConnection(info.connection) &&
                    checkSourceTargetEquality(info.connection) &&
                    checkCompatibility(info.connection.sourceId, info.connection.targetId);
            });
            instance.bind("connectionDetached", function(info) {
                updateConnections(info.connection, true);
            });
            instance.bind("connectionMoved", function(info) {
                updateConnections(info.connection, true);
            });
            instance.bind("contextmenu", function(info) {
                instance.detach(info);
            });
            instance.bind("click", function(info) {
                clickedConnection = info;
                $('#connectionInfoParameters').val(info.parameters);
                $('#connectionInfoDialog').modal();
            });
            instance.draggable(jsPlumb.getSelector(".element"), {
                containment: $("#dropContainer")
            });


            /**
             * Defining an endpoint type can be added to object on the site.
             */
            var endpointType = {
                endpoint: ["Dot", {
                    radius: 12
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
                    curviness: 2000,
                }],
                maxConnections: 1,
                dropOptions: {
                    tolerance: "fit",
                },
            };


            /**
             * Handling click event on elements.
             */
            $(".elementTemplate").click(function() {
                addNewElement(instance,
                              endpointType,
                              $(this).prop("id"), (elementIndex++) + "_" + $(this).prop("id"),
                              $(this).position().top,
                              7);
            });


            /**
             * Handling click event on clear button.
             */
            $("#clearService").click(function(e) {
                instance.detachEveryConnection();
                instance.deleteEveryEndpoint();
                $(".element").remove();

                instance.repaintEverything();
                JsPlumbUtil.consume(e);

                elementIndex = 0;
            });


            /**
             * Handling click event on save button.
             */
            $("#saveService").click(function() {
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

                $.each($(".element"), function(index) {
                    instanceSet.push({
                        "displayId": $(this).prop("id"),
                        "posX": Math.floor($(this).position().left),
                        "posY": Math.floor($(this).position().top),
                        "anchors": $(this).attr("anchors")
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
                    }
                });
            });

            $(window).resize(function() {
                $(".element").each(function() {
                    if ($(this).position().left + $(this).width() > $("#dropContainer").position().left + $("#dropContainer").width()) {
                        $(this).css("left", $("#dropContainer").position().left + $("#dropContainer").width() - $(this).width() + 4);
                    }
                });
                instance.repaintEverything();
            });

            $("#dragContainerScrollUp").click(function() {
                if (dragContainerScroll > 0) dragContainerScroll -= 1;
                $("#dragContainer").scrollTop(dragContainerScroll * $("#elementTemplatePanel").height());
            });

            $("#dragContainerScrollDown").click(function() {
                if (dragContainerScroll < $(".elementTemplate").length - 3) dragContainerScroll += 1;
                $("#dragContainer").scrollTop(dragContainerScroll * $("#elementTemplatePanel").height());
            });

            $("#searchElementTemplate").keyup(function() {
                $(".elementTemplate").each(function() {
                    $(this).parent().parent().hide();
                    if ($(this).attr("alt").toLowerCase().indexOf($("#searchElementTemplateInput").val().toLowerCase()) >= 0) {
                        $(this).parent().parent().show();
                    }
                });
            });


            /**
             * Handling click event on dialog save button.
             */
            $("#connectionInfoSave").click(function() {
                clickedConnection.parameters = $("#connectionInfoParameters").val();
            });


            /**
             * Handling page load event.
             */
            $(document).ready(function() {
                $.post("", {
                    event: "loadService"
                }, function(resultValue) {
                    var result = jQuery.parseJSON(resultValue);
                    $("#serviceName").text(result.serviceName);

                    $.each(result.elements, function(i, element) {
                        addNewElement(instance,
                                      endpointType,
                                      element.displayId.split('_')[1],
                                      element.displayId,
                                      element.posY + "px",
                                      element.anchors,
                                      element.parameters,
                                      element.posX + "px");
                        if (elementIndex < element.displayId.split('_')[0]) {
                            elementIndex = element.displayId.split('_')[0];
                        }
                    });
                    elementIndex++;

                    $.each(result.elementConnections, function(i, connection) {
                        var connectionObject = instance.connect({
                            uuids: [connection.sourceEndpoint, connection.targetEndpoint]
                        });
                        connectionObject.parameters = connection.parameters;
                    });
                });
            });
        });
    });
})();