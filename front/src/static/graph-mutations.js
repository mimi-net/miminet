const postJson = function(url, data) {
    $.ajax({
        type: 'POST',
        url: url,
        data: JSON.stringify(data),
        success: function(data) {},
        error: function(err) { console.log('POST failed: ' + url); },
        contentType: "application/json",
        dataType: 'json'
    });
}

const PostNodesEdges = function(){ postJson('/post_nodes_edges?guid=' + network_guid, [nodes, edges, jobs]); }
const PostNodes = function(){ postJson('/post_network_nodes?guid=' + network_guid, nodes); }
const MoveNodes = function(){ postJson('/move_network_nodes?guid=' + network_guid, nodes); }

const addInterfaceToNode = function(node, edge_id) {
    const type = node.config.type;

    if (type === 'host' || type === 'router' || type === 'server') {
        let iface_id = InterfaceUid();
        node.interface.push({ id: iface_id, name: iface_id, connect: edge_id });
    } else if (type === 'l2_switch') {
        let vlan = null;
        let type_connection = null;
        if (areInterfaceFieldsFilled(node)) {
            vlan = 1;
            type_connection = 0;
        }
        let iface_id = l2SwitchPortUid(node.data.id);
        node.interface.push({ id: iface_id, name: iface_id, connect: edge_id, vlan: vlan, type_connection: type_connection });
    } else if (type === 'l1_hub') {
        let iface_id = l1HubPortUid(node.data.id);
        node.interface.push({ id: iface_id, name: iface_id, connect: edge_id });
    }
}

const AddEdge = function(source_id, target_id) {
    let source_node = nodes.find(n => n.data.id === source_id);
    let target_node = nodes.find(n => n.data.id === target_id);

    if (!source_node || !target_node) return;

    SaveNetworkObject();

    let edge_id = EdgeUid();
    edges.push({
        data: { id: edge_id, source: source_node.data.id, target: target_node.data.id }
    });

    addInterfaceToNode(source_node, edge_id);
    addInterfaceToNode(target_node, edge_id);
}

const DeleteJob = function(node_id) {
    jobs = jobs.filter(function(job) {
        return !job || job.host_id !== node_id;
    });
}

const removeInterfacesForEdge = function(node, edge_id) {
    node.interface = node.interface.filter(function(iface) {
        return iface.connect !== edge_id;
    });
}

const DeleteNode = function(node_id) {
    let n = nodes.find(n => n.data.id === node_id);
    if (!n) return;

    // Remove interfaces from connected nodes and collect edge IDs to delete
    const edgeIdsToDelete = new Set();

    edges.forEach(function(edge) {
        if (!edge) return;

        let other_node_id = null;
        if (edge.data.source === node_id) other_node_id = edge.data.target;
        else if (edge.data.target === node_id) other_node_id = edge.data.source;
        else return;

        let other = nodes.find(t => t.data.id === other_node_id);
        if (!other) {
            console.log("We have an edge without target node");
            return;
        }

        removeInterfacesForEdge(other, edge.data.id);
        edgeIdsToDelete.add(edge.data.id);
    });

    edges = edges.filter(function(edge) {
        return edge && !edgeIdsToDelete.has(edge.data.id);
    });

    nodes = nodes.filter(function(node) {
        return node.data.id !== node_id;
    });
}

const DeleteEdge = function(edge_id) {
    let ed = edges.find(ed => ed.data.id === edge_id);
    if (!ed) return;

    [ed.data.source, ed.data.target].forEach(function(node_id) {
        let t = nodes.find(t => t.data.id === node_id);
        if (!t) {
            console.log("We have an edge without target node");
            return;
        }
        removeInterfacesForEdge(t, edge_id);
    });

    let edge_index = edges.findIndex(prop => prop.data.id === edge_id);
    edges.splice(edge_index, 1);
}
