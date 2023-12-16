let SimulationId = 0;
let global_cy = undefined;
let global_eh = undefined;
var NetworkUpdateTimeoutId = -1;
let NetworkCache = [];

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

const RouterUid = function(){

    let host_name = "router_";

    for (let host_number = 1; host_number < 100; host_number++) {
        host = host_name + host_number;

        t = nodes.find(t => t.data.id === host);

        if (!t)
        {
            return host;
        }
    }

    return "router_" + uid();
}

const ServerUid = function(){

    let host_name = "server_";

    for (let host_number = 1; host_number < 100; host_number++) {
        host = host_name + host_number;

        let t = nodes.find(t => t.data.id === host);

        if (!t)
        {
            return host;
        }
    }

    return "server_" + uid();
}

const ShowHostConfig = function(n, shared = 0){

    let hostname = n.config.label;
    hostname = hostname || n.data.id;

    // Create form
    if (shared){
        SharedConfigHostForm(n.data.id);
    } else {
        ConfigHostForm(n.data.id);
    }

    // Add hostname
    ConfigHostName(hostname);

    // Add jobs
    let host_jobs = [];

    if (jobs){
        host_jobs = jobs.filter(j => j.host_id === n.data.id);
    }

    ConfigHostJob(host_jobs, shared);

    // Add interfaces
    $.each(n.interface, function (i) {
        let iface_id = n.interface[i].id;

        if (!iface_id){
            return;
        }

        let connect_id = n.interface[i].connect;

        if (!connect_id){
            return;
        }

        let edge = edges.find(e => e.data.id === connect_id);

        if (!edge){
            return;
        }

        let source_host = edge.data.source;
        let target_host = edge.data.target;

        if (!source_host || !target_host){
            return;
        }

        let connected_to = target_host;
        if (n.data.id === target_host){
            connected_to = source_host;
        }

        let connected_to_host = nodes.find(n => n.data.id === connected_to);
        let connected_to_host_label = "Unknown";

        if (connected_to_host){
            connected_to_host_label = connected_to_host.data.label;
        }

        ip_addr = n.interface[i].ip;

        if (!ip_addr){
            ip_addr = '';
        }

        netmask = n.interface[i].netmask;

        if (!netmask){
            netmask = '';
        }

        ConfigHostInterface(iface_id, ip_addr, netmask, connected_to_host_label);

    });

    if(n.interface.length)
    {
        let default_gw = '';

        if ("default_gw" in n.config){
            default_gw = n.config.default_gw;
        }

        ConfigHostGateway(default_gw);
    }

    if (shared){
        DisableFormInputs();
    }
}

const ShowRouterConfig = function(n, shared = 0){

    let hostname = n.config.label;
    hostname = hostname || n.data.id;

    // Create form
    if (shared){
        SharedConfigRouterForm(n.data.id)
    } else {
        ConfigRouterForm(n.data.id);
    }

    // Add hostname
    ConfigRouterName(hostname);

    // Add jobs
    let router_jobs = [];

    if (jobs){
        router_jobs = jobs.filter(j => j.host_id === n.data.id);
    }

    ConfigRouterJob(router_jobs, shared);

    // Add interfaces
    $.each(n.interface, function (i) {
        let iface_id = n.interface[i].id;

        if (!iface_id){
            return;
        }

        let connect_id = n.interface[i].connect;

        if (!connect_id){
            return;
        }

        let edge = edges.find(e => e.data.id === connect_id);

        if (!edge){
            return;
        }

        let source_host = edge.data.source;
        let target_host = edge.data.target;

        if (!source_host || !target_host){
            return;
        }

        let connected_to = target_host;
        if (n.data.id === target_host){
            connected_to = source_host;
        }

        let connected_to_host = nodes.find(n => n.data.id === connected_to);
        let connected_to_host_label = "Unknown";

        if (connected_to_host){
            connected_to_host_label = connected_to_host.data.label;
        }

        ip_addr = n.interface[i].ip;

        if (!ip_addr){
            ip_addr = '';
        }

        netmask = n.interface[i].netmask;

        if (!netmask){
            netmask = '';
        }

        ConfigRouterInterface(iface_id, ip_addr, netmask, connected_to_host_label);

    });

    if(n.interface.length)
    {
        let default_gw = '';

        if ("default_gw" in n.config){
            default_gw = n.config.default_gw;
        }

        ConfigRouterGateway(default_gw);
    }

    if (shared){
        DisableFormInputs();
    }
}

const ShowHubConfig = function(n, shared = 0){

    let hostname = n.config.label;
    hostname = hostname || n.data.id;

    // Create form
    if (shared){
        SharedConfigHubForm(n.data.id);
    } else {
        ConfigHubForm(n.data.id);
    }

    // Add hostname
    ConfigHubName(hostname);

    if (shared){
        DisableFormInputs();
    }
}

const ShowSwitchConfig = function(n, shared = 0){

    let hostname = n.config.label;
    hostname = hostname || n.data.id;

    // Create form
    if (shared){
        SharedConfigSwitchForm(n.data.id);
    } else {
        ConfigSwitchForm(n.data.id);
    }

    // Add hostname
    ConfigSwitchName(hostname);

    //Add checkbox STP
    ConfigSwtichSTP(n.config.stp);

    if (shared){
        DisableFormInputs();
    }
}

const ShowEdgeConfig = function(edge_id, shared = 0){

    let ed = edges.find(ed => ed.data.id === edge_id);

    if (!ed){
        return;
    }

    let edge_source = ed.data.source;
    let edge_target = ed.data.target;

    // Create form
    ConfigEdgeForm(edge_id);

    // Add source and target info
    ConfigEdgeEndpoints(edge_source, edge_target);

    if (shared){
        DisableFormInputs();
    }
}

const PacketUid = function(){
    return "pkt_" + uid();
}

const ShowServerConfig = function(n, shared = 0){

    let hostname = n.config.label;
    hostname = hostname || n.data.id;

    // Create form
    if (shared){
        SharedConfigServerForm(n.data.id);
    } else {
        ConfigServerForm(n.data.id);
    }

    // Add hostname
    ConfigServerName(hostname);

    // Add jobs
    let host_jobs = [];

    if (jobs){
        host_jobs = jobs.filter(j => j.host_id === n.data.id);
    }

    ConfigServerJob(host_jobs, shared);

    // Add interfaces
    $.each(n.interface, function (i) {
        let iface_id = n.interface[i].id;

        if (!iface_id){
            return;
        }

        let connect_id = n.interface[i].connect;

        if (!connect_id){
            return;
        }

        let edge = edges.find(e => e.data.id === connect_id);

        if (!edge){
            return;
        }

        let source_host = edge.data.source;
        let target_host = edge.data.target;

        if (!source_host || !target_host){
            return;
        }

        let connected_to = target_host;
        if (n.data.id === target_host){
            connected_to = source_host;
        }

        let connected_to_host = nodes.find(n => n.data.id === connected_to);
        let connected_to_host_label = "Unknown";

        if (connected_to_host){
            connected_to_host_label = connected_to_host.data.label;
        }

        ip_addr = n.interface[i].ip;

        if (!ip_addr){
            ip_addr = '';
        }

        netmask = n.interface[i].netmask;

        if (!netmask){
            netmask = '';
        }

        ConfigServerInterface(iface_id, ip_addr, netmask, connected_to_host_label);

    });

    if(n.interface.length)
    {
        let default_gw = '';

        if ("default_gw" in n.config){
            default_gw = n.config.default_gw;
        }

        ConfigServerGateway(default_gw);
    }

    if (shared){
        DisableFormInputs();
    }
}

const l1HubUid = function(){

    let hub_name = "l1hub";

    for (let hub_number = 1; hub_number < 100; hub_number++) {
        hub = hub_name + hub_number;

        t = nodes.find(t => t.data.id === hub);

        if (!t)
        {
            return hub;
        }
    }

    return "hub_" + uid();
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

const l1HubPortUid = function(hub_id){

    let t = nodes.find(t => t.data.id === hub_id);

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
    return "iface_" + Math.random().toString(9).substring(2, 10);
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

        // Save the network state.
        SaveNetworkObject();

        // Add edge
        let edge_id = EdgeUid();

        edges.push({
            data: {
                id: edge_id,
                source: source_node.data.id,
                target: target_node.data.id,
            }
        });

        // Add interface If edge connects to host or to router or to server
        if (source_node.config.type === 'host' || source_node.config.type === 'router' || source_node.config.type === 'server'){
            let iface_id = InterfaceUid();
            source_node.interface.push({
                  id: iface_id,
                  name: iface_id,
                  connect: edge_id,
            });
        }

        if (target_node.config.type === 'host' || target_node.config.type === 'router' || target_node.config.type === 'server'){
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

        // Add interface if connected to Hub
        if (target_node.config.type === 'l1_hub'){
            let iface_id = l1HubPortUid(target_node.data.id);
            target_node.interface.push({
                id: iface_id,
                name: iface_id,
                connect: edge_id,
            });
        }

        if (source_node.config.type === 'l1_hub'){
            let iface_id = l1HubPortUid(source_node.data.id);
            source_node.interface.push({
                id: iface_id,
                name: iface_id,
                connect: edge_id,
            });
        }
}

const DeleteJob = function(node_id){

    let jobs_to_delete = [];

    $.each(jobs , function(idx, job) {

        if (!job){
            return;
        }

        if (job.host_id === node_id){
            jobs_to_delete.push(idx);
        }
    });

    $.each(jobs_to_delete, function (idx, val){
        jobs.splice(val, 1);
    });
}

const DeleteNode = function(node_id) {

    // Find node in nodes
    let n = nodes.find(n => n.data.id === node_id);

    if (!n) {
        return;
    }

    let edges_to_delete = [];

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
    let node_index = nodes.findIndex(prop => prop.data.id === node_id);
    nodes.splice(node_index,1);
}

const DeleteEdge = function (edge_id) {

    let ed = edges.find(ed => ed.data.id === edge_id);

    if (!ed){
        return;
    }

    let connected_nodes = [ed.data.source, ed.data.target];
    let iterator = connected_nodes.values();

    for (let node_id of iterator){
        let t = nodes.find(t => t.data.id === node_id);

        if (!t){
            console.log("We have an edge without target node");
            continue;
        }

        // Iterate interface and delete one
        let edge_node_iface = t.interface.filter(function( iface ) {
            return iface.connect !== edge_id;
        });

        t.interface = edge_node_iface;
    }

    // Delete the edeg
    let edge_index = edges.findIndex(prop => prop.data.id === edge_id);
    edges.splice(edge_index,1);
    return;
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

        let label = ele.data('label') || '';
        let n = nodes.find(n => n.data.id === ele.data('id'));

        if (!n){
            return label;
        }

        $.each(n.interface, function (i) {

            let ip_addr = n.interface[i].ip;
            let netmask = n.interface[i].netmask;

            if (!ip_addr || !netmask){
                return;
            }

            label = label + '\n' + ip_addr + "/" + netmask;
        }
        );

        if (n.config.default_gw)
        {
            label = label + '\n' + 'gw:' + n.config.default_gw;
        }

        $.each(jobs, function (i) {
            let j = jobs[i];

            if (j.host_id === n.data.id){
                label = label + '\n' + '(' + j.print_cmd + ')';
            }

        });

        return label;
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
          'text-wrap': 'wrap'
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
            'border-width': '0px',
            'text-wrap': 'wrap'
        })

        .selector('.hidden')
        .css({
            'display': 'none'
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

const DrawGraph = function() {

    // Do we already have one?
    let cy = undefined;

    if (global_cy)
    {
        cy = global_cy;

        var collection = cy.elements();
        cy.remove(collection);
        cy.autounselectify(true);
        cy.add(nodes);
        cy.add(edges);
        cy.nodes().grabify();
        global_eh.enable();
        return;
    }

    cy = cytoscape({
        container: document.getElementById("network_scheme"),
        boxSelectionEnabled: true,
        autounselectify: true,
        style: prepareStylesheet(),
        elements: [],
        layout: 'preset',
        zoom: network_zoom,
        pan: { x: network_pan_x, y: network_pan_y },
        fit: true,
    });

    global_cy = cy;

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

    global_eh = cy.edgehandles(defaults);

    cy.minZoom(0.5);
    cy.maxZoom(2);

    cy.add(nodes);
    cy.add(edges);

    // Changing zoom
    cy.on('zoom', function(evt){

        if (NetworkUpdateTimeoutId >= 0){
            clearTimeout(NetworkUpdateTimeoutId);
            NetworkUpdateTimeoutId = -1;
        }

        NetworkUpdateTimeoutId = setTimeout(UpdateNetworkConfig, 2000);
    });

    // Changing the pan
    cy.on('pan', function(evt){

        if (NetworkUpdateTimeoutId >= 0){
            clearTimeout(NetworkUpdateTimeoutId);
            NetworkUpdateTimeoutId = -1;
        }

        NetworkUpdateTimeoutId = setTimeout(UpdateNetworkConfig, 2000);
    });

    // Looking for a position changing
    cy.on('dragfree', 'node', function(evt){

        //let node_id = evt.target.id();
        let n = nodes.find(n => n.data.id === this.id());

        if (!n) {
            return;
        }

        n.position.x = this.position().x;
        n.position.y = this.position().y;

        MoveNodes();
        TakeGraphPictureAndUpdate();
    });

    // Click on object
    cy.on('click', function (evt) {

        let evtTarget = evt.target;

        // Is this cy ?
        if (evtTarget === cy) {
            ClearConfigForm('');
            selecteed_node_id = 0;
            selected_edge_id = 0;
            return;
        }

        // Is this edge ?
        if (evtTarget.group() === 'edges'){
            selected_edge_id = evtTarget.data().id;
            ShowEdgeConfig(selected_edge_id);
            selecteed_node_id = 0;
            return;
        }

        // Maybe host ?
        var target_id = evt.target.id();
        let n = nodes.find(n => n.data.id === target_id);

        if (!n) {
            return;
        }

        selecteed_node_id = n.data.id;
        selected_edge_id = 0;

        if (n.config.type === 'host'){
            ShowHostConfig(n);
        } else if (n.config.type === 'l1_hub'){
            ShowHubConfig(n);
        } else if (n.config.type === 'l2_switch'){
            ShowSwitchConfig(n);
        } else if (n.config.type === 'router'){
            ShowRouterConfig(n);
        } else if (n.config.type === 'server'){
            ShowServerConfig(n);
        }
    });

    // Add edge to the edges[] and then save it to the server.
    cy.on('ehcomplete', (event, sourceNode, targetNode, addedEdge) => {
        AddEdge(sourceNode._private.data.id, targetNode._private.data.id);
        PostNodesEdges();
        TakeGraphPictureAndUpdate();

        SetNetworkPlayerState(-1);
    });

    $(document).on('keyup', function(e){

        if (e.keyCode == 46 && selecteed_node_id) {

            // Save the network state.
            SaveNetworkObject();

            DeleteNode(selecteed_node_id);
            DeleteJob(selecteed_node_id);

            ClearConfigForm('');
            selecteed_node_id = 0;
            selected_edge_id = 0;

            PostNodesEdges();               // Update network on server
            cy.elements().remove();
            cy.add(nodes);
            cy.add(edges);

            TakeGraphPictureAndUpdate();

            // Reset network state
            SetNetworkPlayerState(-1);
        }
        if (e.keyCode ==  46 && selected_edge_id) {

            // Save the network state.
            SaveNetworkObject();

            DeleteEdge(selected_edge_id);

            ClearConfigForm('');
            selecteed_node_id = 0;
            selected_edge_id = 0;

            PostNodesEdges();               // Update network on server
            cy.elements().remove();
            cy.add(nodes);
            cy.add(edges);

            TakeGraphPictureAndUpdate();

            // Reset network state
            SetNetworkPlayerState(-1);
        }

        if (e.keyCode == 90 && e.ctrlKey){

            ClearConfigForm('');
            selecteed_node_id = 0;
            selected_edge_id = 0;

            RestoreNetworkObject();

            PostNodesEdges();               // Update network on server
            cy.elements().remove();
            cy.add(nodes);
            cy.add(edges);

            TakeGraphPictureAndUpdate();

            // Reset network state
            SetNetworkPlayerState(-1);
        }

    });
}

const DrawGraphStatic = function(nodes, edges, shared=0) {

    // Do we already have one?
    let cy = undefined;

    let network_scheme_id = "network_scheme";

    if (shared){
        network_scheme_id = "network_scheme_shared";
    }

    if (global_cy)
    {
        cy = global_cy;
        cy.elements().remove();
    } else {
        cy = cytoscape({
            container: document.getElementById(network_scheme_id),
            boxSelectionEnabled: true,
            autounselectify: false,
            style: prepareStylesheet(),
            elements: [],
            layout: 'preset',
            zoom: network_zoom,
            pan: { x: network_pan_x, y: network_pan_y },
            fit: true,
        });

         global_cy = cy;
    }

    // Turn off edges creation.
    if (global_eh){
        global_eh.disable();
    }

    cy.autounselectify(false);
    cy.add(nodes);
    cy.add(edges);
    cy.nodes().ungrabify();
    return;
}

const DrawSharedGraph = function(nodes, edges) {

    // Do we already have one?
    let cy = undefined;

    if (global_cy)
    {
        cy = global_cy;
        cy.elements().remove();
    } else {
        cy = cytoscape({
            container: document.getElementById("network_scheme_shared"),
            boxSelectionEnabled: true,
            autounselectify: true,
            style: prepareStylesheet(),
            elements: [],
            layout: 'preset',
            zoom: network_zoom,
            pan: { x: network_pan_x, y: network_pan_y },
            fit: true,
        });

        global_cy = cy;
    }

    cy.autounselectify(true);

    cy.minZoom(0.5);
    cy.maxZoom(2);

    cy.add(nodes);
    cy.add(edges);

    // Click on object
    cy.on('click', function (evt) {

        let evtTarget = evt.target;
        if (evtTarget === cy) {
            ClearConfigForm('');
            selecteed_node_id = 0;
            selected_edge_id = 0;
            return;
        }

        // Is this edge ?
        if (evtTarget.group() === 'edges'){
            selected_edge_id = evtTarget.data().id;
            ShowEdgeConfig(selected_edge_id);
            selecteed_node_id = 0;
            return;
        }

        var target_id = evt.target.id();
        let n = nodes.find(n => n.data.id === target_id);

        if (!n) {
            return;
        }

        selecteed_node_id = n.data.id;
        selected_edge_id = 0;

        if (n.config.type === 'host'){
            ShowHostConfig(n, shared=1);
        } else if (n.config.type === 'l1_hub'){
            ShowHubConfig(n, shared=1);
        } else if (n.config.type === 'l2_switch'){
            ShowSwitchConfig(n, shared=1);
        } else if (n.config.type === 'router'){
            ShowRouterConfig(n, shared=1);
        } else if (n.config.type === 'server'){
            ShowServerConfig(n, shared=1);
        }
    });
}

const DrawIndexGraphStatic = function(nodes, edges, container_id, graph_network_zoom,
                                    graph_network_pan_x, graph_network_pan_y)
{

    let index_cy = cytoscape({
        container: document.getElementById(container_id),
        boxSelectionEnabled: true,
        autounselectify: false,
        style: prepareStylesheet(),
        elements: [],
        layout: 'preset',
        zoom: graph_network_zoom,
            pan: { x: graph_network_pan_x, y: graph_network_pan_y },
            fit: true,
        });

    index_cy.autounselectify(false);

    index_cy.add(nodes);
    index_cy.add(edges);
    index_cy.panningEnabled(false);

    index_cy.nodes().ungrabify();
    return index_cy;
}

// Check whether simulation is over and we can run packets
const CheckSimulation = function (simulation_id)
{
    $.ajax({
        type: 'GET',
        url: '/check_simulation?simulation_id=' + simulation_id + '&network_guid=' + network_guid,
        data: '',
        success: function(data, textStatus, xhr) {

            // If we got 210 (processing) wait 2 sec and call themself again
            if (xhr.status === 210)
            {
                setTimeout(CheckSimulation, 2000, simulation_id);
            }

            // Simulation is ended up and we can grab the packets
            if (xhr.status === 200)
            {
                packets = JSON.parse(data.packets);
                pcaps = data.pcaps;
                SetNetworkPlayerState(0);
            }
        },
        error: function(xhr) {
            console.log('Cannot check simulation id = ' + simulation_id);
            SetNetworkPlayerState(-1);
        },
        contentType: "application/json",
        dataType: 'json'
    });
}

// Update host configuration
const UpdateHostConfiguration = function (data, host_id)
{
    // Reset network player
    SetNetworkPlayerState(-1);

    $.ajax({
        type: 'POST',
        url: '/host/save_config',
        data: data,
        success: function(data, textStatus, xhr) {

            if (xhr.status === 200)
            {
                if (!data.warning){

                    // Update nodes
                    nodes = data.nodes;

                    // Update jobs
                    jobs = data.jobs;

                    // Update graph
                    DrawGraph();
                }

                // Ok, let's try to update host config form
                let n = nodes.find(n => n.data.id === host_id);

                if (!n) {
                    ClearConfigForm('Нет такого хоста');
                    return;
                }

                if (n.config.type === 'host'){
                    ShowHostConfig(n);
                } else {
                    ClearConfigForm('Узел есть, но это не хост');
                    return;
                }

                if (data.warning){
                    HostWarningMsg(data.warning);
                }
            }
        },
        error: function(xhr) {
            console.log('Не удалось обновить конфигурацию хоста');
            console.log(xhr);
        },
        dataType: 'json'
    });
}

// Delete job from host
const DeleteJobFromHost = function (host_id, job_id, network_guid)
{
    // Reset network player
    SetNetworkPlayerState(-1);

    let data = {
      id: job_id,
      guid: network_guid,
    };

    $.ajax({
        type: 'POST',
        url: '/host/delete_job',
        data: data,
        encode: true,
        success: function(data, textStatus, xhr) {

            if (xhr.status === 200)
            {
                // Update jobs
                jobs = data.jobs;

                // Update graph
                DrawGraph();

                // Ok, let's try to update host config form
                let n = nodes.find(n => n.data.id === host_id);

                if (!n) {
                    ClearConfigForm('Нет такого хоста');
                    return;
                }

                if (n.config.type === 'host'){
                    ShowHostConfig(n);
                } else {
                    ClearConfigForm('Узел есть, но это не хост');
                }

            }
        },
        error: function(xhr) {
            console.log('Не удалось удалить команду');
            console.log(xhr);
        },
        dataType: 'json'
    });
}

// Delete job from router
const DeleteJobFromRouter = function (router_id, job_id, network_guid)
{
    // Reset network player
    SetNetworkPlayerState(-1);

    let data = {
      id: job_id,
      guid: network_guid,
    };

    $.ajax({
        type: 'POST',
        url: '/host/delete_job',
        data: data,
        encode: true,
        success: function(data, textStatus, xhr) {

            if (xhr.status === 200)
            {
                // Update jobs
                jobs = data.jobs;

                // Update graph
                DrawGraph();

                // Ok, let's try to update host config form
                let n = nodes.find(n => n.data.id === router_id);

                if (!n) {
                    ClearConfigForm('Нет такого хоста');
                    return;
                }

                if (n.config.type === 'router'){
                    ShowRouterConfig(n);
                } else {
                    ClearConfigForm('Узел есть, но это не раутер');
                }
            }
        },
        error: function(xhr) {
            console.log('Не удалось удалить команду');
            console.log(xhr);
        },
        dataType: 'json'
    });
}

// Delete job from server
const DeleteJobFromServer = function (server_id, job_id, network_guid)
{
    // Reset network player
    SetNetworkPlayerState(-1);

    let data = {
      id: job_id,
      guid: network_guid,
    };

    $.ajax({
        type: 'POST',
        url: '/host/delete_job',
        data: data,
        encode: true,
        success: function(data, textStatus, xhr) {

            if (xhr.status === 200)
            {
                // Update jobs
                jobs = data.jobs;

                // Update graph
                DrawGraph();

                // Ok, let's try to update host config form
                let n = nodes.find(n => n.data.id === server_id);

                if (!n) {
                    ClearConfigForm('Нет такого хоста');
                    return;
                }

                if (n.config.type === 'server'){
                    ShowServerConfig(n);
                } else {
                    ClearConfigForm('Узел есть, но это не сервер');
                }
            }
        },
        error: function(xhr) {
            console.log('Не удалось удалить команду');
            console.log(xhr);
        },
        dataType: 'json'
    });
}

// Update router configuration
const UpdateRouterConfiguration = function (data, router_id)
{
    // Reset network player
    SetNetworkPlayerState(-1);

    $.ajax({
        type: 'POST',
        url: '/host/router_save_config',
        data: data,
        success: function(data, textStatus, xhr) {

            if (xhr.status === 200)
            {
                // Update nodes
                if (data.nodes)
                {
                    nodes = data.nodes;
                }

                // Update jobs
                if (data.jobs)
                {
                    jobs = data.jobs;
                }

                // Update graph
                DrawGraph();

                // Ok, let's try to update router config form
                let n = nodes.find(n => n.data.id === router_id);

                if (!n) {
                    ClearConfigForm('Нет такого раутера');
                    return;
                }

                if (n.config.type === 'router'){
                    ShowRouterConfig(n);
                } else {
                    ClearConfigForm('Узел есть, но это не раутер');
                    return;
                }

                if (data.warning)
                {
                    HostWarningMsg(data.warning);
                }
            }

        },
        error: function(xhr) {
            console.log('Не удалось обновить конфигурацию хоста');
            console.log(xhr);
        },
        dataType: 'json'
    });
}

// Update server configuration
const UpdateServerConfiguration = function (data, router_id)
{
    // Reset network player
    SetNetworkPlayerState(-1);

    $.ajax({
        type: 'POST',
        url: '/host/server_save_config',
        data: data,
        success: function(data, textStatus, xhr) {

            if (xhr.status === 200)
            {

                if (!data.warning){

                    if (data.nodes){
                        nodes = data.nodes;
                    }

                    if (data.jobs){
                        jobs = data.jobs;
                    }

                    // Update graph
                    DrawGraph();
                }

                // Ok, let's try to update router config form
                let n = nodes.find(n => n.data.id === router_id);

                if (!n) {
                    ClearConfigForm('Нет такого сервера');
                    return;
                }

                if (n.config.type === 'server'){
                    ShowServerConfig(n);
                } else {
                    ClearConfigForm('Узел есть, но это не сервер');
                    return;
                }

                if (data.warning)
                {
                    ServerWarningMsg(data.warning);
                }
            }

        },
        error: function(xhr) {
            console.log('Не удалось обновить конфигурацию сервера');
            console.log(xhr);
        },
        dataType: 'json'
    });
}

// Update hub configuration
const UpdateHubConfiguration = function (data, hub_id)
{
    $.ajax({
        type: 'POST',
        url: '/host/hub_save_config',
        data: data,
        success: function(data, textStatus, xhr) {

            if (xhr.status === 200)
            {
                // Update nodes
                nodes = data.nodes;

                // We don't clear packets and RunButtonState.
                // Hub can change only names

                // Update graph
                DrawGraph();

                // Ok, let's try to update host config form
                let n = nodes.find(n => n.data.id === hub_id);

                if (!n) {
                    ClearConfigForm('Нет такого узла');
                    return;
                }

                if (n.config.type === 'l1_hub'){
                    ShowHubConfig(n);
                } else {
                    ClearConfigForm('Нет такого хаба');
                }
            }
        },
        error: function(xhr) {
            console.log('Cannot update host config');
            console.log(xhr);
        },
        dataType: 'json'
    });
}

// Update Switch configuration
const UpdateSwitchConfiguration = function (data, switch_id)
{
    // Reset network player
    SetNetworkPlayerState(-1);

    $.ajax({
        type: 'POST',
        url: '/host/switch_save_config',
        data: data,
        success: function(data, textStatus, xhr) {

            if (xhr.status === 200)
            {
                // Update nodes
                nodes = data.nodes;

                // We don't clear packets and RunButtonState.
                // Hub can change only names

                // Update graph
                DrawGraph();

                // Ok, let's try to update host config form
                let n = nodes.find(n => n.data.id === switch_id);

                if (!n) {
                    ClearConfigForm('Нет такого узла');
                    return;
                }

                if (n.config.type === 'l2_switch'){
                    ShowSwitchConfig(n);
                } else {
                    ClearConfigForm('Нет такого свитча');
                }
            }
        },
        error: function(xhr) {
            console.log('Cannot update host config');
            console.log(xhr);
        },
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
            SetNetworkPlayerState(-1);
        },
        contentType: "application/json",
        dataType: 'json'
    });
}

// 2 states:
// Do we need emulation
// We have a packets and ready to play packets
const SetNetworkPlayerState = function(simultaion_id)
{

    // Reset?
    if (simultaion_id === -1){
        packets = null;
        pcaps = [];
        SetNetworkPlayerState(0);
        return;
    }

    // If we have packets, than we're ready to run
    if (packets)
    {
        $('#NetworkPlayer').empty();
        $('#NetworkPlayer').append('<button type="button" class="btn btn-danger me-2" id="NetworkStopButton"><i class="bx bx-stop fs-xl"></i></button>');
        $('#NetworkPlayer').append('<button type="button" class="btn btn-success" id="NetworkPlayPauseButton"><i class="bx bx-play fs-xl"></i></button>');

        // Init player
        PacketPlayer.getInstance().InitPlayer(packets);

        // Configure the slider
        $('#PacketSliderInput')[0].noUiSlider.updateOptions({
            start: [1],
            range: {
                'min': 1,
                'max': packets.length,
            },
            format: {
                to: function (val){return '' + val},
                from: function (val){return '' + val},
            },
            tooltips: false,
        });

        // Show Slider on
        $('#PacketSliderInput').show();

        const pkt_count = packets.reduce((currentCount, row) => currentCount + row.length, 0);
        $('#NetworkPlayerLabel').text(packets.length + ' ' + NumWord(packets.length, ['шаг', 'шага', 'шагов']) + ' / ' + pkt_count + ' ' + NumWord(pkt_count, ['пакет', 'пакета', 'пакетов']));

        $('#PacketSliderInput')[0].noUiSlider.on('slide', function (e) {
            if (!e) return;
            let x =  Math.round(e[0]);
            PacketPlayer.getInstance().setAnimationTrafficStep(x-1);
        });

        $('#PacketSliderInput')[0].noUiSlider.on('update', function (e) {
            if (!e) return;
            let x =  Math.round(e[0]);
            if (packets.length === 0){
                $('#NetworkPlayerLabel').text('0 пакетов');
                return;
            }
            $('#NetworkPlayerLabel').text('Шаг: ' + x + '/' + packets.length + ' (' +  packets[x-1].length + ' ' + NumWord(packets[x-1].length, ['пакет', 'пакета', 'пакетов']) + ')');
        });

        // Set click handlers
        $('#NetworkPlayPauseButton').click(function() {

            // If btn-success then start to play
            if ($(this).hasClass("btn-success")){
                $(this).removeClass('btn-success');
                $(this).addClass('btn-warning');

                $(this).empty();
                $(this).append('<i class="bx bx-pause fs-xl"></i>');

                // If not in pause. Draw a new layout and go.
                if (!PacketPlayer.getInstance().getPlayerPause())
                {
                    DrawGraphStatic(nodes, edges);
                }

                PacketPlayer.getInstance().setAnimationTrafficStepCallback(function() {
                    $('#PacketSliderInput')[0].noUiSlider.set(PacketPlayer.getInstance().getAnimationTrafficStep());
                });

                PacketPlayer.getInstance().StartPlayer(global_cy);
                return;
            } else {

                $(this).removeClass('btn-warning');
                $(this).addClass('btn-success');
                $(this).empty();
                $(this).append('<i class="bx bx-play fs-xl"></i>');

                PacketPlayer.getInstance().PausePlayer();
                return;
            }
        });

        $('#NetworkStopButton').click(function() {

            PacketPlayer.getInstance().resetAnimationTrafficStepCallback();
            PacketPlayer.getInstance().StopPlayer();

            // Reset slider.
            $('#PacketSliderInput')[0].noUiSlider.set(0);

            DrawGraph(nodes, edges);

            $('#NetworkPlayPauseButton').removeClass('btn-success');
            $('#NetworkPlayPauseButton').removeClass('btn-warning');
            $('#NetworkPlayPauseButton').empty();
            $('#NetworkPlayPauseButton').addClass('btn-success');
            $('#NetworkPlayPauseButton').append('<i class="bx bx-play fs-xl"></i>');
            return;
        });

        return;
    }

    // No packets.
    // The network is simulating?
    if (simultaion_id)
    {
        $('#NetworkPlayer').empty();
        $('#PacketSliderInput').hide();
        $('#NetworkPlayer').append('<button type="button" class="btn btn-primary w-100" id="NetworkEmulateButton" disabled>Эмулируется...</button>');
        $('#NetworkPlayerLabel').text("Ожидание 10-20 сек.");
        CheckSimulation(simultaion_id);
        return;
    }

    // No packets and no simulation.
    // Add emulation button.
    $('#NetworkPlayer').empty();
    $('#PacketSliderInput').hide();
    $('#NetworkPlayer').append('<button type="button" class="btn btn-primary w-100" id="NetworkEmulateButton">Эмулировать</button>');
    $('#NetworkPlayerLabel').text("Ожидание 10-20 сек.");

    $('#NetworkEmulateButton').click(function() {

        // Check for job. If no job - show modal and exit.
        if (!jobs.length)
        {
            $('#noJobsModal').modal('toggle');
            return;
        }

        RunSimulation(network_guid);

        $('#NetworkPlayer').empty();
        $('#NetworkPlayer').append('<button type="button" class="btn btn-primary w-100" id="NetworkEmulateButton" disabled>Эмулируется...</button>');
        $('#NetworkPlayerLabel').text("Ожидание 10-20 сек.");
        return;
    });

    return;

}

// 2 states:
// No packets - disable button.
// We have a packets and ready to play packets
const SetSharedNetworkPlayerState = function()
{

    // If we have packets, than we're ready to run
    if (packets)
    {
        $('#NetworkPlayer').empty();
        $('#NetworkPlayer').append('<button type="button" class="btn btn-danger me-2" id="NetworkStopButton"><i class="bx bx-stop fs-xl"></i></button>');
        $('#NetworkPlayer').append('<button type="button" class="btn btn-success" id="NetworkPlayPauseButton"><i class="bx bx-play fs-xl"></i></button>');

        // Init player
        PacketPlayer.getInstance().InitPlayer(packets);

        // Configure the slider
        $('#PacketSliderInput')[0].noUiSlider.updateOptions({
            start: [1],
            range: {
                'min': 1,
                'max': packets.length,
            },
            format: {
                to: function (val){return '' + val},
                from: function (val){return '' + val},
            },
            tooltips: false,
        });

        // Show Slider on
        $('#PacketSliderInput').show();

        const pkt_count = packets.reduce((currentCount, row) => currentCount + row.length, 0);
        $('#NetworkPlayerLabel').text(packets.length + ' ' + NumWord(packets.length, ['шаг', 'шага', 'шагов']) + ' / ' + pkt_count + ' ' + NumWord(pkt_count, ['пакет', 'пакета', 'пакетов']));

        $('#PacketSliderInput')[0].noUiSlider.on('slide', function (e) {
            if (!e) return;
            let x =  Math.round(e[0]);
            PacketPlayer.getInstance().setAnimationTrafficStep(x-1);
        });

        $('#PacketSliderInput')[0].noUiSlider.on('update', function (e) {
            if (!e) return;
            let x =  Math.round(e[0]);
            if (packets.length === 0){
                $('#NetworkPlayerLabel').text('0 пакетов');
                return;
            }
            $('#NetworkPlayerLabel').text('Шаг: ' + x + '/' + packets.length + ' (' +  packets[x-1].length + ' ' + NumWord(packets[x-1].length, ['пакет', 'пакета', 'пакетов']) + ')');
        });

        // Set click handlers
        $('#NetworkPlayPauseButton').click(function() {

            // If btn-success then start to play
            if ($(this).hasClass("btn-success")){
                $(this).removeClass('btn-success');
                $(this).addClass('btn-warning');

                $(this).empty();
                $(this).append('<i class="bx bx-pause fs-xl"></i>');

                // If not in pause. Draw a new layout and go.
                if (!PacketPlayer.getInstance().getPlayerPause())
                {
                    DrawGraphStatic(nodes, edges);
                }

                PacketPlayer.getInstance().setAnimationTrafficStepCallback(function() {
                    $('#PacketSliderInput')[0].noUiSlider.set(PacketPlayer.getInstance().getAnimationTrafficStep());
                });

                PacketPlayer.getInstance().StartPlayer(global_cy);
            } else {
                $(this).removeClass('btn-warning');
                $(this).addClass('btn-success');
                $(this).empty();
                $(this).append('<i class="bx bx-play fs-xl"></i>');

                PacketPlayer.getInstance().PausePlayer();
                return;
            }
        });

        $('#NetworkStopButton').click(function() {

            PacketPlayer.getInstance().resetAnimationTrafficStepCallback();
            PacketPlayer.getInstance().StopPlayer();

            // Reset slider.
            $('#PacketSliderInput')[0].noUiSlider.set(0);

            DrawSharedGraph(nodes, edges);

            $('#NetworkPlayPauseButton').removeClass('btn-success');
            $('#NetworkPlayPauseButton').removeClass('btn-warning');
            $('#NetworkPlayPauseButton').empty();
            $('#NetworkPlayPauseButton').addClass('btn-success');
            $('#NetworkPlayPauseButton').append('<i class="bx bx-play fs-xl"></i>');
            return;
        });

        return;
    }

    // No packets
    // Add info button
    $('#NetworkPlayer').empty();
    $('#PacketSliderInput').hide();
    $('#NetworkPlayer').append('<button type="button" class="btn btn-primary w-100" id="NetworkEmulateButton" disabled>Нет эмуляции</button>');
    return;
}

// Take a picture and update it.
const TakeGraphPictureAndUpdate = function()
{
    if (!global_cy)
    {
        return;
    }

    let png_blob = global_cy.png({output: 'blob', maxWidth: 512, maxHeight: 512});

    $.ajax({
        type: 'POST',
        url: '/network/upload_network_picture?guid=' + network_guid,
        data: png_blob,
        processData: false,
        error: function(xhr) {

            if (xhr.status != 200){
                console.log('Cannot upload graph picture');
            }

        },
        dataType: 'image/png'
    });
}

// Calculate drop offsets
const CalculateDropOffset = function(elem_x, elem_y)
{
    const network_scheme = document.getElementById("network_scheme");
    let offset_left = 0;
    let offset_top = 0;
    let ret = {'x' : 0, 'y' : 0};

    console.log(elem_x + ", " + elem_y);

    if (network_scheme){
        ret.x += network_scheme.offsetLeft - 25;
        ret.y += network_scheme.offsetTop - 15;
    }

    if (global_cy)
    {
        ret.x = ret.x + global_cy.pan().x;
        ret.y = ret.y + global_cy.pan().y;

        ret.x = (elem_x - ret.x) / global_cy.zoom();
        ret.y = (elem_y - ret.y) / global_cy.zoom();
    }

    return ret;
}

const UpdateNetworkConfig = function()
{
    if (!global_cy){
        return;
    }

    let data = {'network_title' : network_title, 'network_description' : network_description,
    'zoom' : global_cy.zoom(),'pan_x' : global_cy.pan().x, 'pan_y' : global_cy.pan().y};

    $.ajax({
        type: 'POST',
        url: '/network/update_network_config?guid=' + network_guid,
        data: JSON.stringify(data),
        contentType: "application/json; charset=utf-8",
        success: function(data, textStatus, xhr) {
        },
        error: function(xhr) {
            console.log('Cannot update network config');
            console.log(xhr);
        },
        dataType: 'json'
    });

}

const CopyNetwork = function ()
{
    $.ajax({
        type: 'POST',
        url: '/network/copy_network?guid=' + network_guid,
        data: '',
        success: function(data, textStatus, xhr) {
            if (xhr.status === 200)
            {
                console.log("Copy network is made.");
                $('#ModalCopy').modal('show');
                $('.modal-option').click(function() {
                var selectedOption = $(this).attr('data-option');
                    if (selectedOption === 'edit') {
                        var newUrl = data.new_url;
                        window.location.href = newUrl;
                        console.log('Go to editing');
                    } else if (selectedOption === 'continue') {
                        console.log('Continue here');
                    }
                $('#ModalCopy').modal('hide');
                });
            }
        },
        error: function(err) {
            console.log('Copy has not been made.');
        },
        contentType: "application/json",
        dataType: 'json'
    });
}


const NumWord = function (value, words){
	value = Math.abs(value) % 100;
	var num = value % 10;
	if(value > 10 && value < 20) return words[2];
	if(num > 1 && num < 5) return words[1];
	if(num == 1) return words[0];
	return words[2];
}

const SaveNetworkObject = function (){
    let n = JSON.parse(JSON.stringify(nodes));
    let e = JSON.parse(JSON.stringify(edges));

    NetworkCache.push({
        nodes: n,
        edges: e,
    });

    return 0;
}

const RestoreNetworkObject = function (){
    let x = NetworkCache.pop();

    if (!x){
        return;
    }

    nodes=x.nodes;
    edges=x.edges;

    return 0;
}