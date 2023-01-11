let NetworkState = 0; // 0 - not simulated yet, 1 - simulating, 2 - ready to run, 3 - animated
let SimulationId = 0;

const uid = function(){
    return Date.now().toString(36) + Math.random().toString(36).substr(2);
}

const HostUid = function(){

    let host_name = "host_";

    for (let host_number = 1; host_number < 100; host_number++) {
        host = host_name + host_number;

        t = nodes.find(t => t.data.id === host);

        if (!t)
        {
            return host;
        }
    }

    return "host_" + uid();
}

const PacketUid = function(){
    return "pkt_" + uid();
}

const l2SwitchUid = function(){

    let sw_name = "l2sw";

    for (let sw_number = 1; sw_number < 100; sw_number++) {
        sw = sw_name + sw_number;

        t = nodes.find(t => t.data.id === sw);

        if (!t)
        {
            return sw;
        }
    }

    return "sw_" + uid();
}

const l2SwitchPortUid = function(switch_id){

    let t = nodes.find(t => t.data.id === switch_id);

    if (!t)
    {
        return -1;
    }

    for (let port_number = 1; port_number < 128; port_number++) {
        port = t.data.id + "_" + port_number;

        let i = t.interface.find(i => i.id === port);

        if (!i){
            return port;
        }
    }
}

const EdgeUid = function(){
    return "edge_" + uid();
}

const InterfaceUid = function(){
    return "iface_" + Math.random().toString(9).substr(12);
}

const PostEdges = function(){
    $.ajax({
        type: 'POST',
        url: '/post_network_edges?guid=' + network_guid,
        data: JSON.stringify(edges),
        success: function(data) {},
        error: function(err) {console.log('Cannot post edges to server')},
        contentType: "application/json",
        dataType: 'json'
    });
}

const PostNodesEdges = function(){
    $.ajax({
        type: 'POST',
        url: '/post_nodes_edges?guid=' + network_guid,
        data: JSON.stringify([nodes, edges]),
        success: function(data) {},
        error: function(err) {console.log('Cannot post edges to server')},
        contentType: "application/json",
        dataType: 'json'
    });
}

const AddEdge = function(source_id, target_id){

        let source_node = nodes.find(n => n.data.id === source_id);
        let target_node = nodes.find(n => n.data.id === target_id);

        // Do we find nodes?
        if (!source_node || !target_node)
        {
            return;
        }

        // Add edge
        let edge_id = EdgeUid();

        edges.push({
            data: {
                id: edge_id,
                source: source_node.data.id,
                target: target_node.data.id,
            }
        });

        // Add interface If edge connects to host
        if (source_node.config.type === 'host'){
            let iface_id = InterfaceUid();
            source_node.interface.push({
                  id: iface_id,
                  name: iface_id,
                  connect: edge_id,
            });
        }

        if (target_node.config.type === 'host'){
            let iface_id = InterfaceUid();
            target_node.interface.push({
                id: iface_id,
                name: iface_id,
                connect: edge_id,
            });
        }

        // Add interface if connected to switch
        if (target_node.config.type === 'l2_switch'){
            let iface_id = l2SwitchPortUid(target_node.data.id);
            target_node.interface.push({
                id: iface_id,
                name: iface_id,
                connect: edge_id,
            });
        }

        if (source_node.config.type === 'l2_switch'){
            let iface_id = l2SwitchPortUid(source_node.data.id);
            source_node.interface.push({
                id: iface_id,
                name: iface_id,
                connect: edge_id,
            });
        }
}

const DeleteNode = function(node_id) {

    // Find node in nodes
    let n = nodes.find(n => n.data.id === node_id);

    if (!n) {
        return;
    }

    edges_to_delete = []

    // Find all edges that connected to the deleted node
    $.each(edges , function(idx, edge) {

        if (!edge){
            return;
        }

        // Find the edge
        if (edge.data.source === node_id)
        {
            // Find the node on the other side
            let t = nodes.find(t => t.data.id === edge.data.target);

            if (!t){
                console.log("We have an edge without target node");
                return;
            }

            // Iterate interface and delete one
            let new_iface = t.interface.filter(function( iface ) {
                return iface.connect !== edge.data.id;
            });

            t.interface = new_iface;
            edges_to_delete.unshift(idx);
            return;
        }

        if (edge.data.target === node_id)
        {
            // Find the node on the other side
            let t = nodes.find(t => t.data.id === edge.data.source);

            if (!t){
                console.log("We have an edge without target node");
                return;
            }

            // Iterate interface and delete one
            let new_iface = t.interface.filter(function( iface ) {
                return iface.connect !== edge.data.id;
            });

            t.interface = new_iface;
            edges_to_delete.unshift(idx);
            return;
        }

    });

    $.each(edges_to_delete, function (idx, val){
        edges.splice(val, 1);
    });

    // Delete the node
    let node_index = nodes.findIndex(prop => prop.data.id === node_id)
    nodes.splice(node_index,1)
    PostNodesEdges();
    DrawGraph(nodes, edges);

}

const PostNodes = function(){
    $.ajax({
        type: 'POST',
        url: '/post_network_nodes?guid=' + network_guid,
        data: JSON.stringify(nodes),
        success: function(data) {},
        error: function(err) {console.log('Cannot post nodes to server')},
        contentType: "application/json",
        dataType: 'json'
    });
}

const MoveNodes = function(){
    $.ajax({
        type: 'POST',
        url: '/move_network_nodes?guid=' + network_guid,
        data: JSON.stringify(nodes),
        success: function(data) {},
        error: function(err) {console.log('Cannot post nodes to server')},
        contentType: "application/json",
        dataType: 'json'
    });
}

const prepareStylesheet = function() {
    const getColor = function(ele) {
      return ele.data('color') || '#ffaaaa';
    };
    const getEdgeLabel = function(ele) {
      return ele.data('label') || '';
    };
    const getLineStyle = function(ele) {
      return ele.data('line') || 'solid';
    };
    const getCurveStyle = function(ele) {
      return ele.data('style') || 'bezier';
    };
    const getTextDirection = function(ele) {
      return ele.data('direction') || 'autorotate';
    };
    const getNodeLabel = function(ele) {
      // return ele.data('label') || ele.data('id');
        return ele.data('label') || '';
    };
    let sheet = cytoscape.stylesheet()
        .selector('node')
        .css({
          'height': 30,
          'width': 30,
          'background-fit': 'cover',
          'border-color': '#000',
          'border-width': 0,
          'content': getNodeLabel,
          'text-valign': 'top',
          'text-align': 'center',
            'font-size': '8px',
        })
        .selector('edge')
        .css({
          'width': 2,
          'target-arrow-shape': 'none',
          'line-color': getColor,
          'target-arrow-color': getColor,
          'curve-style': getCurveStyle,
          'label': getEdgeLabel,
          'line-style': getLineStyle,
          'color': '#000',
          'text-outline-color': '#FFF',
          'text-outline-width': 1,
          'edge-text-rotation': getTextDirection,
        })
        .selector('.eh-handle')
        .css({
            'background-color': 'red',
            'width': 8,
            'height': 8,
            'shape': 'ellipse',
            'overlay-opacity': 0,
            'border-width': 4, // makes the handle easier to hit
            'border-opacity': 0
        })

        .selector('.eh-hover')
        .css({
            'background-color': 'red'
        })

        .selector('.eh-source')
        .css({
            'border-width': 2,
            'border-color': 'red'
        })

        .selector('.eh-target')
        .css({
            'border-width': 2,
            'border-color': 'red'
        })

        .selector('.eh-preview')
        .css({
            'background-color': 'red',
            'line-color': 'red',
            'target-arrow-color': 'red',
            'source-arrow-color': 'red'
        })

        .selector('.eh-ghost-edge')
        .css({
            'background-color': 'red',
            'line-color': 'red',
            'target-arrow-color': 'red',
            'source-arrow-color': 'red'
        })

        .selector('node[name]')
        .css({
            'content': 'data(name)'
        })

        .selector('node[type="packet"]')
        .css({
            'content': 'data(label)',
            'text-valign': 'top',
            'text-align': 'center',
            'height': '5px',
            'width': '5px',
            'border-opacity': '0',
            'border-width': '0px'
        })

        .selector('.eh-ghost-edge.eh-preview-active')
        .css({
            'opacity': 0
        });

    const appendIconClass = function(stylesheet, cssClass) {
      return stylesheet.selector('.' + cssClass)
          .css({
            'background-image': DiagramIcons[cssClass],
            'background-opacity': 0,
            'border-width': 0,
            'background-clip': 'none',
          });
    };

    for (const prop in DiagramIcons) {

      if (Object.prototype.hasOwnProperty.call(DiagramIcons, prop)) {
        sheet = appendIconClass(sheet, prop);
      }
    }

    return sheet;
  };

const DrawGraph = function(nodes, edges) {

    const cy = cytoscape({
        container: document.getElementById("network_scheme"),
        boxSelectionEnabled: true,
        autounselectify: true,
        style: prepareStylesheet(),
        elements: [],
        layout: 'preset',
        zoom: 2,
        fit: true,
    });

    // the default values of each option are outlined below:
    let defaults = {
        canConnect: function( sourceNode, targetNode ){

            // whether an edge can be created between source and target
        return !sourceNode.same(targetNode); // e.g. disallow loops
        },

        edgeParams: function( sourceNode, targetNode ){

            // for edges between the specified source and target
            // return element object to be passed to cy.add() for edge
            return {};
        },

        hoverDelay: 150, // time spent hovering over a target node before it is considered selected
        snap: true, // when enabled, the edge can be drawn by just moving close to a target node (can be confusing on compound graphs)
        snapThreshold: 50, // the target node must be less than or equal to this many pixels away from the cursor/finger
        snapFrequency: 15, // the number of times per second (Hz) that snap checks done (lower is less expensive)
        noEdgeEventsInDraw: true, // set events:no to edges during draws, prevents mouseouts on compounds
        disableBrowserGestures: true // during an edge drawing gesture, disable browser gestures such as two-finger trackpad swipe and pinch-to-zoom
    };

    let eh = cy.edgehandles(defaults );

    cy.add(nodes);
    cy.add(edges);

    // Looking for a position changing
    cy.on('mouseup', 'node', function (evt) {

        var node = evt.target;
        let n = nodes.find(n => n.data.id === this.id());

        if (!n) {
            return;
        }

        nx = n.renderedPosition.x;
        ny = n.renderedPosition.y;

        pos = node.renderedPosition();
        rx = pos.x;
        ry = pos.y;

        if ((nx != rx) || (ny != ry)) {
            n.renderedPosition.x = rx;
            n.renderedPosition.y = ry;
            MoveNodes();
            console.log("Change node position from: x=" + nx + ", y=" + ny + " to x=" + rx + ", y=" + ry);
        }
    });

    // Click on object
    cy.on('click', 'node', function (evt) {
        var node = evt.target;
        let n = nodes.find(n => n.data.id === this.id());

        if (!n) {
            return;
        }

        selecteed_node_id = n.data.id;

        if (n.config.type === 'host'){

            let hostname = n.data.label;
            hostname = hostname || n.data.id;

            // Create form
            ConfigHostForm(n.data.id);

            // Add hostname
            ConfigHostName(hostname);

            // Add interfaces
            $.each(n.interface, function (i) {
                iface_name = n.interface[i].name;

                if (!iface_name){
                    return;
                }

                ip_addr = n.interface[i].ip;

                if (!ip_addr){
                    ip_addr = '';
                }

                netmask = n.interface[i].netmask;

                if (!netmask){
                    netmask = '';
                }

                ConfigHostInterface(iface_name, ip_addr, netmask);

            });
            //ConfigHostInterface(hostname);
        }
    });

    // Add edge to the edges[] and then save it to the server.
    cy.on('ehcomplete', (event, sourceNode, targetNode, addedEdge) => {
        AddEdge(sourceNode._private.data.id, targetNode._private.data.id);
        PostNodesEdges();

        // Reset network state
        if (GetNetworkState()){
            SetNetworkRunButtonState(0, null);
        }
    });

    $(document).on('keyup', function(e){

    if (e.keyCode ==  46)
        {
            DeleteNode(selecteed_node_id);
        }
    });

}

const RunPackets = function (cy, pkts){

    let zoom = cy.zoom();

    pkts.forEach(function(p_item){

        let edge = cy.edges('[id = "' + p_item['config']['path'] + '"]');

        if (!edge.source()) {
            return;
        }

        let pkt_id = p_item['data']['id'];
        let from_xy = undefined;
        let to_xy = undefined;

        if (edge.source().id() === p_item['config']['source']){
            console.log('From source to target');

            from_xy = edge.sourceEndpoint();
            to_xy = edge.targetEndpoint();

        } else if (edge.source().id() === p_item['config']['target'])
        {
            console.log("From target to source");

            from_xy = edge.targetEndpoint();
            to_xy = edge.sourceEndpoint();

        } else {
            console.log('Got edge but source and target id is not equal');
            return;
        }

        p_item['renderedPosition'] = {x: from_xy['x'] * zoom, y: from_xy['y'] * zoom};
        cy.add(p_item);

        cy.nodes().last().animate({
            renderedPosition: {x: to_xy['x'] * zoom, y: to_xy['y'] * zoom}
        }, {
            duration: 1000,
            complete: function(){
                cy.remove('[id = "' + pkt_id + '"]');
            }
        });
    })
}

const DrawGraphStatic = function(nodes, edges, traffic) {

    const cy = cytoscape({
        container: document.getElementById("network_scheme"),
        boxSelectionEnabled: true,
        autounselectify: false,
        style: prepareStylesheet(),
        elements: [],
        layout: 'preset',
        zoom: 2,
        fit: true,
    });

    cy.add(nodes);
    cy.add(edges);

    let timeout = 0;

    traffic.forEach(function(pkts){
        setTimeout(function(){RunPackets(cy, pkts)}, timeout);
        timeout += 1500;
    })

    setTimeout(function(){$('#NetworkRunButton').click();}, timeout);

    cy.nodes().ungrabify();
    return;
}

const GetNetworkState = function()
{
    return NetworkState;
}

const SetNetworkState = function(state)
{
    NetworkState = state;
    return NetworkState;
}

// Check whether simulation is over and we can run packets
const CheckSimulation = function (simulation_id)
{
    $.ajax({
        type: 'GET',
        url: '/check_simulation?simulation_id=' + simulation_id,
        data: '',
        success: function(data, textStatus, xhr) {

            // If we got 210 (processing) wait 1 sec and call themself again
            if (xhr.status === 210)
            {
                setTimeout(CheckSimulation, 2000, simulation_id);
            }

            if (xhr.status === 200)
            {
                packets = JSON.parse(data.packets);
                console.log(data);
                SetNetworkRunButtonState(0, packets)
            }
        },
        error: function(xhr) {
            console.log('Cannot check simulation id = ' + simulation_id);
            SetNetworkRunButtonState(0, null);
        },
        contentType: "application/json",
        dataType: 'json'
    });
}

const RunSimulation = function (network_guid)
{
    $.ajax({
        type: 'POST',
        url: '/run_simulation?guid=' + network_guid,
        data: '',
        success: function(data, textStatus, xhr) {
            if (xhr.status === 201)
            {
                console.log("Simulation is running!");
                // Ok, run CheckSimulation
                if (data.simulation_id)
                {
                    CheckSimulation(data.simulation_id);
                }
            }
        },
        error: function(err) {
            console.log('Cannot run simulation guid = ' + network_guid);
        },
        contentType: "application/json",
        dataType: 'json'
    });

}

const SetNetworkRunButtonState = function(id, packets)
{
    // If we have packets, than we're ready to run
    if (packets)
    {
        $('#NetworkRunButton').text('Запустить');
        $('#NetworkRunButton').removeClass('btn-primary');
        $('#NetworkRunButton').addClass('btn-success');
        $('#NetworkRunButton').prop('disabled', false);

        SetNetworkState(2);
        return;
    }

    // Don't have a packets (not simulated yet). Do we have simulation id?
    // If so, we're simulating.
    if (id)
    {
        $('#NetworkRunButton').text('Симуляция');
        $('#NetworkRunButton').removeClass('btn-primary');
        $('#NetworkRunButton').addClass('btn-secondary');
        $('#NetworkRunButton').prop('disabled', true);

        CheckSimulation(id);
        SetNetworkState(1);
        return;
    }

    $('#NetworkRunButton').text('Симулировать');
    $('#NetworkRunButton').removeClass('btn-secondary');
    $('#NetworkRunButton').removeClass('btn-success');
    $('#NetworkRunButton').addClass('btn-primary');
    $('#NetworkRunButton').prop('disabled', false);
    SetNetworkState(0);
    return;
}