const PostNodesEdges = function(){
    ajaxWithAuth({
        type: 'POST',
        url: ExternalUrlFor('/post_nodes_edges?guid=' + network_guid),
        data: JSON.stringify([nodes, edges, jobs]),
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
            var vlan = null;
            var type_connection = null;

            if (areInterfaceFieldsFilled(target_node)) {
                vlan = 1;
                type_connection = 0;
            }

            let iface_id = l2SwitchPortUid(target_node.data.id);
            target_node.interface.push({
                id: iface_id,
                name: iface_id,
                connect: edge_id,
                vlan: vlan,
                type_connection: type_connection,
            });
        }

        if (source_node.config.type === 'l2_switch'){
            var vlan = null;
            var type_connection = null;

            if (areInterfaceFieldsFilled(source_node)) {
                vlan = 1;
                type_connection = 0;
            }

            let iface_id = l2SwitchPortUid(source_node.data.id);
            source_node.interface.push({
                id: iface_id,
                name: iface_id,
                connect: edge_id,
                vlan: vlan,
                type_connection: type_connection,
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
    jobs_to_delete.reverse()
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
    ajaxWithAuth({
        type: 'POST',
        url: ExternalUrlFor('/post_network_nodes?guid=' + network_guid),
        data: JSON.stringify(nodes),
        success: function(data) {},
        error: function(err) {console.log('Cannot post nodes to server')},
        contentType: "application/json",
        dataType: 'json'
    });
}

const MoveNodes = function(){

    ajaxWithAuth({
        type: 'POST',
        url: ExternalUrlFor('/move_network_nodes?guid=' + network_guid),
        data: JSON.stringify(nodes),
        success: function(data) {},
        error: function(err) {console.log('Cannot post nodes to server')},
        contentType: "application/json",
        dataType: 'json'
    });
}

const prepareStylesheet = function() {
    const getColor = function(ele) {
        if (ele.group() === "edges") {
            const dup = ele.data('duplicate_percentage');
            if (dup > 0) {
                return '#26AE31';
            }
        }
        return ele.data('color') || '#9FBFE5';
    };
    const getEdgeLabel = function(ele) {
      return ele.data('label') || '';
    };
    const getLineStyle = function(ele) {
      if (ele.group() === "edges") {
        const loss = ele.data('loss_percentage');
        if (loss > 0) {
          return 'dashed';
        }
      }
      return ele.data('line') || 'solid';
    };
    const getLineDashPattern = function(ele) {
      if (ele.group() === "edges") {
        const loss = ele.data('loss_percentage');
        if (loss > 0) {
          const gap = 2 + Math.round((loss / 100) * 18);
          return [6, gap];
        }
      }
      return [6, 0];
    };
    const getCurveStyle = function(ele) {
      return ele.data('style') || 'bezier';
    };
    const getTextDirection = function(ele) {
      return ele.data('direction') || 'autorotate';
    };

     const getPeerLabelByEdge = function(edgeId, selfId) {
        const e = edges.find(ed => ed.data && ed.data.id === edgeId);
        if (!e) return null;
        const otherId = (e.data.source === selfId) ? e.data.target : e.data.source;
        const n = nodes.find(nn => nn.data && nn.data.id === otherId);
        return (n && n.data && n.data.label) ? n.data.label : otherId;
    };

    const buildVlanLine = function(swNode, iface) {
        if (iface == null) return '';
        const vlan = iface.vlan;
        if (vlan === null || vlan === undefined) return '';
        const peer = getPeerLabelByEdge(iface.connect, swNode.data.id) || '';
        let mode = 'Access';
        if (iface.type_connection === 1) mode = 'Trunk';
        const vlanStr = Array.isArray(vlan) ? vlan.join(',') : vlan;
        return `(${peer} VLAN ${vlanStr} ${mode})`;
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

        if (n.config && n.config.type === 'l2_switch') {
            const stpMode = n.config.stp || 0;
            if (stpMode > 0) {
                const proto = (stpMode === 2) ? 'rstp on' : 'stp on';
                const pr = (n.config.priority !== undefined && n.config.priority !== null)
                    ? ` prior ${n.config.priority}` : '';
                label = label + '\n' + `(${proto}${pr})`;
            }
            if (Array.isArray(n.interface)) {
                n.interface.forEach((iface) => {
                    const vlanLine = buildVlanLine(n, iface);
                    if (vlanLine) label = label + '\n' + vlanLine;
                });
            }
        }

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
          'line-dash-pattern': getLineDashPattern,
          'color': '#000',
          'text-outline-color': '#FFF',
          'text-outline-width': 1,
          'edge-text-rotation': getTextDirection,
        })
        .selector('.eh-handle')
        .css({
            'background-color': 'blue',
            'width': 8,
            'height': 8,
            'shape': 'ellipse',
            'overlay-opacity': 0,
            'border-width': 4, // makes the handle easier to hit
            'border-opacity': 0
        })

        .selector('.eh-hover')
        .css({
            'background-color': 'blue'
        })

        .selector('.eh-source')
        .css({
            'border-width': 2,
            'border-color': 'blue'
        })

        .selector('.eh-target')
        .css({
            'border-width': 2,
            'border-color': 'blue'
        })

        .selector('.eh-preview')
        .css({
            'background-color': 'blue',
            'line-color': 'blue',
            'target-arrow-color': 'blue',
            'source-arrow-color': 'blue'
        })

        .selector('.eh-ghost-edge')
        .css({
            'background-color': 'blue',
            'line-color': 'blue',
            'target-arrow-color': 'blue',
            'source-arrow-color': 'blue'
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
        })

        .selector('edge.link-down')
        .css({
            'line-color': '#E8A838',
        })

        .selector('edge.link-down-active')
        .css({
            'line-color': '#999',
            'opacity': 0.5,
            'width': 1,
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

const SnapNodesToGrid = function(cy_instance) {
    if (!cy_instance) return;

    let anyMoved = false;
    const baseGridSize = 25;

    cy_instance.nodes().each(function(ele) {
        if (!ele.isNode()) return;

        const pos = ele.position();
        
        // Calculate snapped position
        const newX = Math.round(pos.x / baseGridSize) * baseGridSize;
        const newY = Math.round(pos.y / baseGridSize) * baseGridSize;
        
        // If coordinate differs significantly (float error)
        if (Math.abs(newX - pos.x) > 0.5 || Math.abs(newY - pos.y) > 0.5) {
            
            // Move cy node
            ele.position({x: newX, y: newY});
            
            // Update global nodes array
            if (typeof nodes !== 'undefined') {
                 let n = nodes.find(n => n.data.id === ele.id());
                 if (n) {
                     n.position.x = newX;
                     n.position.y = newY;
                     anyMoved = true;
                 }
            }
        }
    });

    if (anyMoved) {
        MoveNodes();
    }
}

const FindEdgeIdByJob = function(job) {
    const node = nodes.find(n => n.data.id === job.host_id);
    if (!node || !Array.isArray(node.interface)) return null;
    const iface = node.interface.find(i => i.id === job.arg_1);
    return iface?.connect || null;
};

const MarkLinkDownEdges = function(cy_instance) {
    if (!cy_instance) return;

    cy_instance.edges('.link-down, .link-down-active')
        .removeClass('link-down')
        .removeClass('link-down-active')
        .removeStyle();

    jobs.forEach(function(j) {
        if (j.job_id == LINK_DOWN_JOB_ID) {
            const edgeId = FindEdgeIdByJob(j);
            if (edgeId) {
                cy_instance.edges('[id="' + edgeId + '"]').addClass('link-down');
            }
        }
    });
};

