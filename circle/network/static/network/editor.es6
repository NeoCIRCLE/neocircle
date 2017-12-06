/* jshint esversion: 6 */

function renderListElement(elem){
  return `
<div class="unused-element"
     type="${ elem.type }"
     description="${ elem.description }"
     id="${ elem.id }"
     icon="${ elem.icon }"
     name="${ elem.name }"
     free_port_num="${ elem.free_port_num }">
  <i class="fa ${ elem.type == 'vm' ? 'fa-desktop' : 'fa-sitemap' }"></i>
  ${ elem.name }
</div>`;
}

function renderBoardElement(elem){
  return `
<div class="element"
     name="${ elem.name }"
     type="${ elem.type }"
     id="${ elem.id }"
     description="${ elem.description }"
     icon="${ elem.icon }"
     free_port_num="${ elem.free_port_num }"
     ondragstart="return false;">
  <i class="fa ${ elem.type == 'vm' ? 'fa-desktop' : 'fa-sitemap'}"></i> 
  ${ elem.name }
</div>`;
}


var add_interfaces = [];
var remove_interfaces = [];
var old_connections = [];

var add_nodes = new Set();
var remove_nodes = new Set();
var old_nodes = new Set();

function convertConnection(connection) {
    var con = {
        source: connection.source.id,
        target: connection.target.id,
        equals: function(other) {
            return this.source === other.source &&
                   this.target === other.target;
        }
    };

    if(con.source.startsWith('net')){
        var tmp = con.source;
        con.source = con.target;
        con.target = tmp;
    }
    
    con.source = con.source.slice(3);
    con.target = con.target.slice(4);

    return con;
}

function uniqueAddToList(list, value){
    var hit = list.find((val) => {
        return val.equals(value); 
    });
    if(hit) return;
    list.push(value);
}

function removeFromList(list, value){
    var index = list.findIndex((val) => {
        return val.equals(value); 
    });
    if(index === -1) return;
    list.splice(index, 1);
}

function isOldConnection(connection){
  return old_connections.find((val) => {
    return val.equals(connection); 
  });
}

function cleanListElements(list){
  return list.map((value) => {
    return {
      source: value.source,
      target: value.target
    };
  });
}

function addInterface(connection) {
    var con = convertConnection(connection);
    if(!isOldConnection(con))
      uniqueAddToList(add_interfaces, con);
    removeFromList(remove_interfaces, con);
}

function removeInterface(connection) {
    var con = convertConnection(connection);
    if(isOldConnection(con))
      uniqueAddToList(remove_interfaces, con);
    removeFromList(add_interfaces, con);
}

function getNodeId(node) {
  return node.id;
}

function isOldNode(id) {
  return old_nodes.has(id);
}

function addNode(node) {
    var id = getNodeId(node);
    add_nodes.add(id);
    remove_nodes.delete(id);
}

function removeNode(node) {
    var id = getNodeId(node);
    if(isOldNode(id))
      remove_nodes.add(id);
    add_nodes.delete(id);
}

function checkLoopback(connection) {
  return connection.target !== connection.source;
}

function checkCompatibility(connection) {
  var target_type = $(connection.target).attr('type');
  var source_type = $(connection.source).attr('type');

  return target_type !== source_type;
}

// Before the connection is established
function beforeDrop(info) {
  return checkCompatibility(info.connection);
}

function onConnect(info) {
  addInterface(info.connection);
}

function onDetach(info) {
  removeInterface(info.connection);
}

function FakeConnection(sourceId, targetId) {
  this.source = {id: sourceId};
  this.target = {id: targetId};
  return this;
}

function onConnectionMoved(info) {
  var fakeOrigCon = new FakeConnection(info.originalSourceId,
                                   info.originalTargetId);
  removeInterface(fakeOrigCon);
  var fakeNewCon = new FakeConnection(info.newSourceId,
                                   info.newTargetId);
  addInterface(fakeNewCon);
}

function onConnectionAborted(connection) {
  addInterface(connection);
}

function randInt(from, to) {
  if(from > to){
    var tmp = to;
    to = from;
    from = tmp;
  }
  var size = to - from;
  return Math.floor((Math.random() * size) + from);
}

function convertElement(elem) {
  return {
    id: elem.attr('id'),
    type: elem.attr('type'),
    description: elem.attr('description'),
    name: elem.attr('name'),
    icon: elem.attr('icon'),
    free_port_num: elem.attr('free_port_num')
  };
}

function convertListForSaving(list) {
  const getId = (id, type) => 
    (type === 'vm') ?  id.slice(3) : id.slice(4); 
  var retv = [];
  list.forEach( (i, id) => {
    var e=$('#' + id);
    retv.push({
      id: getId(e.attr('id'), e.attr('type')),
      type: e.attr('type'),
      x: e.css('left').replace('px', ''),
      y: e.css('top').replace('px', ''),
      free_port_num: e.attr('free_port_num')
    });
  });
  return retv;
}


class SwitchButton {
  constructor(id, checked) {
    this.element = $('#' + id);
    this.element.css('cursor', 'pointer');
    this.afterChanged(() => {});
    this.setClass(checked);
  }

  setClass(checked){
    this.element.removeClass('fa');
    this.element.removeClass('fa-toggle-on');
    this.element.removeClass('fa-toggle-off');
    this.element.addClass('fa');
    this.element.addClass( checked ? 'fa-toggle-on' : 'fa-toggle-off');
  }

  isChecked() {
    return this.element.hasClass('fa-toggle-on');
  }
  
  afterChanged(func) {
    this.element.off('click');
    var thiz = this;
    this.element.click(function() {
      thiz.setClass(!thiz.isChecked());
      func();
    });
  }
}


jsPlumb.ready(() => {
  var endpointOptions = {
    anchor: 'Continuous',
    isSource: true,
    isTarget: true,
    maxConnections: 1
  };
  var jsPlumbInstance = jsPlumb;

  jsPlumbInstance.setContainer('#dropContainer');
  jsPlumbInstance.bind('beforeDrop', beforeDrop);
  jsPlumbInstance.bind('connection', onConnect);
  jsPlumbInstance.bind('connectionDetached', onDetach);
  jsPlumbInstance.bind('connectionMoved', onConnectionMoved);
  jsPlumbInstance.bind('connectionAborted', onConnectionAborted);

  function connectEndpoints(connection) {
    return jsPlumbInstance.connect(connection, {
      allowLoopback: false,
      newConnection: true,
      anchor: 'Continuous',
      deleteEndpointsOnDetach: true
    });
  }

  function addEndpoint(elem){
    jsPlumbInstance.addEndpoint(elem.id, endpointOptions);
  }

  function generatePosition(){
    var dc = $('#dropContainer');
    var width = dc.css("width").replace('px', '');
    var height = dc.css("height").replace('px', '');
    return {
      x: randInt(0, width),
      y: randInt(0, height)
    };
  }

  function addElementToBoard(element, random) {
    var pos;
    if(random)
      pos = generatePosition();
    else
      pos = {
        x: element.x,
        y: element.y
      };

    var newe = $(renderBoardElement(element))
      .css('top', pos.y + 'px')
      .css('left', pos.x + 'px')[0];

      $('#dropContainer').append(newe);

    for(var i = 0; i < element.free_port_num; ++i){
      addEndpoint(newe);
    }
    jsPlumbInstance.draggable(newe.id, {containment: true});
    jsPlumbInstance.repaint(newe.id);

    $(newe).bind('contextmenu', removeElement);
    jsPlumbInstance.repaintEverything();
  }

  function selectElementFromList(ev) {
    var elem = $(ev.target);
    var obj = convertElement(elem);
    elem.detach();
    addElementToBoard(obj, true);
    addNode(obj);
  }

  function addElementToList(elem) {
    $('#dragContainer').append(renderListElement(elem));
    $('#' + elem.id).click(selectElementFromList);
  }

  function removeElement(ev) {
    var elem = $(ev.target);
    var obj = convertElement(elem);
    jsPlumbInstance.removeAllEndpoints(elem.attr('id'));
    elem.detach();
    addElementToList(obj);
    removeNode(obj);
  }

  function clearWorkspace() {
    jsPlumbInstance.deleteEveryConnection();
    jsPlumbInstance.deleteEveryEndpoint();
    $('.element').detach();
    $('.unused-element').detach();
  }

  function initialize(result){
    clearWorkspace();

    old_nodes = new Set();
    add_nodes = new Set();
    remove_nodes = new Set();

    $.each(result.elements, (i, element) => {
      addElementToBoard(element);
      old_nodes.add(element.id);
      add_nodes.add(element.id);
    });
    $.each(result.nongraph_elements, (i, element) => {
      addElementToBoard(element, true);
      add_nodes.add(element.id);
    });
    $.each(result.unused_elements, (i, element) => {
      addElementToList(element);
    });
    old_connections = [];
    $.each(result.connections, (i, connection) => {
      var con = connectEndpoints(connection);
      old_connections.push(convertConnection(con));
    });
    add_interfaces = []; // Because of a 'connect' event,
                         // connections are added to this list,
                         // but this is not necessary.
    remove_interfaces = [];
  }

  function save() {
    var data = {
      add_interfaces: cleanListElements(add_interfaces),
      remove_interfaces: cleanListElements(remove_interfaces),
      add_nodes: convertListForSaving(add_nodes),
      remove_nodes: convertListForSaving(remove_nodes)
    };
    $.post('', JSON.stringify(data), initialize, 'json');
  }

  $.get('', initialize);
  $("#saveButton").click(save);

  $('#searchField').on('keyup', filter);

  var vmFilter = new SwitchButton('vm-filter', true);
  vmFilter.afterChanged(filter);
  var netFilter = new SwitchButton('net-filter', true);
  netFilter.afterChanged(filter);

  function filter() {
    $(".unused-element").each((i, elem) => {
      elem = $(elem);
      elem.hide();
      var key = $("#searchField").val().toLowerCase();
      var type = elem.attr('type');
      var network_on = netFilter.isChecked();
      var vm_on = vmFilter.isChecked();
      if(elem.attr("name").toLowerCase().indexOf(key) >= 0 &&
         ((type === "network" && network_on) || (type === "vm" && vm_on)))
        elem.show();
    });
  }
 
});
