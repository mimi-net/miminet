let global_cy = undefined;
let global_eh = undefined;
let NetworkUpdateTimeoutId = -1;
let NetworkCache = [];
let lastSimulationId = 0

let packetsNotFiltered = null;
let packetFilterState = {
    hideARP: false,
    hideSTP: false,
    hideSYN: false,
};

let gridCanvasLayer = undefined;
let currentGridZoom = 1.0;
let selectionUpdateTimeout;
let internalClipboard = null;
let lastMousePosition = { x: 0, y: 0 };

// ========== COMMON HELPERS ==========

const clearSelection = function() {
    ClearConfigForm('');
    selecteed_node_id = 0;
    selected_edge_id = 0;
};

const refreshGraphAfterMutation = function(cy) {
    PostNodesEdges();
    cy.elements().remove();
    cy.add(nodes);
    cy.add(edges);
    TakeGraphPictureAndUpdate();
    SetNetworkPlayerState(-1);
};

const debouncedNetworkConfigUpdate = function() {
    if (NetworkUpdateTimeoutId >= 0) {
        clearTimeout(NetworkUpdateTimeoutId);
        NetworkUpdateTimeoutId = -1;
    }
    NetworkUpdateTimeoutId = setTimeout(UpdateNetworkConfig, 2000);
};

const createCytoscapeInstance = function(containerId, options) {
    return cytoscape({
        container: document.getElementById(containerId),
        boxSelectionEnabled: true,
        autounselectify: options.autounselectify || false,
        selectionType: options.selectionType || 'single',
        style: prepareStylesheet(),
        elements: [],
        layout: 'preset',
        zoom: options.zoom || network_zoom,
        pan: { x: options.pan_x || network_pan_x, y: options.pan_y || network_pan_y },
        fit: true,
    });
};

// ========== MULTI-SELECT HELPERS ==========

const showConfigForNode = function(n, shared) {
    if (n.config.type === 'host') ShowHostConfig(n, shared);
    else if (n.config.type === 'l1_hub') ShowHubConfig(n, shared);
    else if (n.config.type === 'l2_switch') ShowSwitchConfig(n, shared);
    else if (n.config.type === 'router') ShowRouterConfig(n, shared);
    else if (n.config.type === 'server') ShowServerConfig(n, shared);
};

const showMultiSelectSummary = function(nodeCount, edgeCount) {
    $(config_content_id).empty();
    $(config_content_save_tag).empty();
    document.getElementById(config_content_save_id).style.display = 'none';

    let html = '<div class="text-center p-3">';
    html += '<div style="font-weight:500; margin-bottom:8px;">Выделено элементов</div>';
    if (nodeCount > 0) {
        html += '<div>' + nodeCount + ' ' + NumWord(nodeCount, ['устройство','устройства','устройств']) + '</div>';
    }
    if (edgeCount > 0) {
        html += '<div>' + edgeCount + ' ' + NumWord(edgeCount, ['соединение','соединения','соединений']) + '</div>';
    }
    html += '<div class="mt-3 text-muted" style="font-size:12px;">Ctrl+C \u2014 копировать<br>Del \u2014 удалить</div>';
    html += '</div>';

    $(config_content_id).append(html);
};

const updateConfigPanelForSelection = function(cy) {
    const selected = cy.elements(':selected');
    if (selected.length === 0) {
        clearSelection();
    } else if (selected.length === 1) {
        const el = selected[0];
        if (el.group() === 'edges') {
            selected_edge_id = el.data().id;
            ShowEdgeConfig(selected_edge_id);
            selecteed_node_id = 0;
        } else {
            let n = nodes.find(n => n.data.id === el.id());
            if (n) {
                selecteed_node_id = n.data.id;
                selected_edge_id = 0;
                showConfigForNode(n);
            }
        }
    } else {
        selecteed_node_id = 0;
        selected_edge_id = 0;
        const nodeCount = selected.nodes().length;
        const edgeCount = selected.edges().length;
        showMultiSelectSummary(nodeCount, edgeCount);
    }
};

const autoSelectConnectingEdges = function(cy) {
    const selectedNodeIds = new Set();
    cy.nodes(':selected').forEach(function(n) { selectedNodeIds.add(n.id()); });

    cy.edges().forEach(function(edge) {
        const srcSelected = selectedNodeIds.has(edge.source().id());
        const tgtSelected = selectedNodeIds.has(edge.target().id());
        if (srcSelected && tgtSelected && !edge.selected()) {
            edge.select();
        }
    });
};

// ========== COPY/PASTE ==========

const buildClipboardPayload = function(cy) {
    const selectedNodeIds = new Set();
    cy.nodes(':selected').forEach(function(ele) {
        selectedNodeIds.add(ele.id());
    });

    if (selectedNodeIds.size === 0) return null;

    // Deep copy selected nodes
    const copiedNodes = [];
    nodes.forEach(function(n) {
        if (selectedNodeIds.has(n.data.id)) {
            copiedNodes.push(JSON.parse(JSON.stringify(n)));
        }
    });

    // Collect only explicitly selected edges (not auto-inferred)
    const selectedEdgeIds = new Set();
    cy.edges(':selected').forEach(function(ele) {
        selectedEdgeIds.add(ele.id());
    });

    const copiedEdges = [];
    const copiedEdgeIds = new Set();
    edges.forEach(function(e) {
        if (selectedEdgeIds.has(e.data.id) &&
            selectedNodeIds.has(e.data.source) && selectedNodeIds.has(e.data.target)) {
            copiedEdges.push(JSON.parse(JSON.stringify(e)));
            copiedEdgeIds.add(e.data.id);
        }
    });

    // Collect jobs for selected nodes
    const copiedJobs = [];
    jobs.forEach(function(j) {
        if (selectedNodeIds.has(j.host_id)) {
            copiedJobs.push(JSON.parse(JSON.stringify(j)));
        }
    });

    // Strip dangling interfaces (those connecting to non-copied edges)
    copiedNodes.forEach(function(n) {
        n.interface = n.interface.filter(function(iface) {
            return copiedEdgeIds.has(iface.connect);
        });
    });

    return {
        miminet_clipboard: true,
        version: 1,
        nodes: copiedNodes,
        edges: copiedEdges,
        jobs: copiedJobs,
    };
};

const showCopyFeedback = function() {
    global_cy.elements(':selected').addClass('copy-flash');
    setTimeout(function() {
        global_cy.elements('.copy-flash').removeClass('copy-flash');
    }, 300);
};

const pasteClipboardData = function(clipboardData) {
    if (!clipboardData || !clipboardData.miminet_clipboard) return;
    if (!clipboardData.nodes || clipboardData.nodes.length === 0) return;

    SaveNetworkObject();

    const nodeIdMap = {};
    const edgeIdMap = {};
    const baseGridSize = 25;

    // Calculate offset: move center of copied elements to cursor position
    let sumX = 0, sumY = 0;
    clipboardData.nodes.forEach(function(n) { sumX += n.position.x; sumY += n.position.y; });
    const centerX = sumX / clipboardData.nodes.length;
    const centerY = sumY / clipboardData.nodes.length;

    // Use cursor position if available, otherwise fallback to +50px offset
    let targetX = centerX + 50;
    let targetY = centerY + 50;
    if (lastMousePosition && lastMousePosition.x !== 0 && lastMousePosition.y !== 0) {
        targetX = lastMousePosition.x;
        targetY = lastMousePosition.y;
    }

    const offsetX = targetX - centerX;
    const offsetY = targetY - centerY;

    // Step 1: Generate new node IDs
    // Push temporary placeholders into nodes[] so each Uid() call
    // sees previously generated IDs as taken
    const tempPlaceholders = [];
    clipboardData.nodes.forEach(function(n) {
        const t = n.config.type;
        let newId;
        if (t === 'host') newId = HostUid();
        else if (t === 'router') newId = RouterUid();
        else if (t === 'server') newId = ServerUid();
        else if (t === 'l2_switch') newId = l2SwitchUid();
        else if (t === 'l1_hub') newId = l1HubUid();
        else return;
        nodeIdMap[n.data.id] = newId;
        // Placeholder so next Uid() call sees this ID as taken
        const placeholder = {data: {id: newId}, config: {type: t}, interface: []};
        nodes.push(placeholder);
        tempPlaceholders.push(placeholder);
    });
    // Remove placeholders before real nodes are added
    tempPlaceholders.forEach(function(p) {
        const idx = nodes.indexOf(p);
        if (idx !== -1) nodes.splice(idx, 1);
    });

    // Step 2: Generate new edge IDs
    clipboardData.edges.forEach(function(e) {
        edgeIdMap[e.data.id] = EdgeUid();
    });

    // Step 3: Transform and push nodes
    clipboardData.nodes.forEach(function(n) {
        const newNodeId = nodeIdMap[n.data.id];
        if (!newNodeId) return;

        n.data.id = newNodeId;
        n.data.label = newNodeId;
        n.config.label = newNodeId;

        // Offset position to cursor and snap to grid
        n.position.x = Math.round((n.position.x + offsetX) / baseGridSize) * baseGridSize;
        n.position.y = Math.round((n.position.y + offsetY) / baseGridSize) * baseGridSize;

        // Remap interfaces
        n.interface.forEach(function(iface) {
            iface.id = InterfaceUid();
            iface.name = iface.id;
            if (iface.connect && edgeIdMap[iface.connect]) {
                iface.connect = edgeIdMap[iface.connect];
            }
        });

        nodes.push(n);
    });

    // Step 4: Transform and push edges
    clipboardData.edges.forEach(function(e) {
        e.data.id = edgeIdMap[e.data.id];
        e.data.source = nodeIdMap[e.data.source];
        e.data.target = nodeIdMap[e.data.target];
        if (e.data.source && e.data.target) {
            edges.push(e);
        }
    });

    // Step 5: Transform and push jobs
    if (clipboardData.jobs) {
        clipboardData.jobs.forEach(function(j) {
            if (nodeIdMap[j.host_id]) {
                j.host_id = nodeIdMap[j.host_id];
                j.id = uid();
                jobs.push(j);
            }
        });
    }

    // Step 6: Save, redraw, select pasted elements
    PostNodesEdges();
    global_cy.elements().remove();
    global_cy.add(nodes);
    global_cy.add(edges);

    // Select newly pasted elements
    global_cy.elements().unselect();
    clipboardData.nodes.forEach(function(n) {
        const cyNode = global_cy.getElementById(n.data.id);
        if (cyNode.length) cyNode.select();
    });
    clipboardData.edges.forEach(function(e) {
        const cyEdge = global_cy.getElementById(e.data.id);
        if (cyEdge.length) cyEdge.select();
    });

    TakeGraphPictureAndUpdate();
    SetNetworkPlayerState(-1);
    updateConfigPanelForSelection(global_cy);
};

const DrawGraph = function() {

    // Do we already have one?
    let cy = undefined;

    if (global_cy)
    {
        cy = global_cy;

        var collection = cy.elements();
        cy.remove(collection);
        cy.autounselectify(false);
        cy.add(nodes);
        cy.add(edges);
        cy.nodes().grabify();
        global_eh.enable();
        return;
    }

    cy = createCytoscapeInstance("network_scheme", {});

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
        snap: false, // when enabled, the edge can be drawn by just moving close to a target node (can be confusing on compound graphs)
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

    // Auto-snap existing network nodes on load
    SnapNodesToGrid(cy);

    // Changing zoom
    cy.on('zoom', function(evt){
        debouncedNetworkConfigUpdate();
        if (gridCanvasLayer) {
            currentGridZoom = cy.zoom();
            drawGrid();
        }
    });

    // Changing the pan
    cy.on('pan', function(evt){
        debouncedNetworkConfigUpdate();
        if (gridCanvasLayer) {
            drawGrid();
        }
    });

    // Looking for a position changing
    cy.on('dragfree', 'node', function(evt){

        //let node_id = evt.target.id();
        let n = nodes.find(n => n.data.id === this.id());

        if (!n) {
            return;
        }

        // Get current position
        let posX = this.position().x;
        let posY = this.position().y;

        // Snap to grid (like draw.io)
        const baseGridSize = 25;
        
        // Snap position to nearest grid intersection
        posX = Math.round(posX / baseGridSize) * baseGridSize;
        posY = Math.round(posY / baseGridSize) * baseGridSize;
        
        // Apply snapped position back to node
        this.position({
            x: posX,
            y: posY
        });

        n.position.x = posX;
        n.position.y = posY;

        MoveNodes();
        TakeGraphPictureAndUpdate();
    });

    // Click on object (supports multi-select with Shift)
    cy.on('click', function (evt) {

        let evtTarget = evt.target;
        const isShift = evt.originalEvent && evt.originalEvent.shiftKey;

        // Click on background
        if (evtTarget === cy) {
            cy.elements().unselect();
            clearSelection();
            return;
        }

        if (!isShift) {
            // Plain click: single-select (preserves existing behavior)
            cy.elements().unselect();
            evtTarget.select();

            if (evtTarget.group() === 'edges') {
                selected_edge_id = evtTarget.data().id;
                ShowEdgeConfig(selected_edge_id);
                selecteed_node_id = 0;
            } else {
                let target_id = evtTarget.id();
                let n = nodes.find(n => n.data.id === target_id);
                if (!n) return;
                selecteed_node_id = n.data.id;
                selected_edge_id = 0;
                showConfigForNode(n);
            }
        } else {
            // Shift+click: Cytoscape already toggled selection,
            // just update config panel
            updateConfigPanelForSelection(cy);
        }
    });

    // Update config panel on box selection changes
    cy.on('select unselect', function() {
        clearTimeout(selectionUpdateTimeout);
        selectionUpdateTimeout = setTimeout(function() {
            updateConfigPanelForSelection(cy);
        }, 50);
    });

    // Guard edgehandles vs box selection conflict
    cy.on('ehstart', function() { cy.boxSelectionEnabled(false); });
    cy.on('ehcomplete ehcancel ehstop', function() { cy.boxSelectionEnabled(true); });

    // Add edge to the edges[] and then save it to the server.
    cy.on('ehcomplete', (event, sourceNode, targetNode, addedEdge) => {
        AddEdge(sourceNode._private.data.id, targetNode._private.data.id);
        PostNodesEdges();
        TakeGraphPictureAndUpdate();

        SetNetworkPlayerState(-1);
    });

    $(document).on('keydown', function(e){

        const evtTarget = e.target;
        if (evtTarget && evtTarget.form) {
            return;
        }

        // Delete: remove all selected elements
        if (e.keyCode == 46) {
            const selected = cy.elements(':selected');
            if (selected.length === 0) return;

            SaveNetworkObject();

            // Delete selected nodes first (DeleteNode also removes connected edges)
            selected.nodes().forEach(function(ele) {
                const nodeId = ele.id();
                DeleteNode(nodeId);
                DeleteJob(nodeId);
            });

            // Delete remaining selected edges
            selected.edges().forEach(function(ele) {
                const edgeId = ele.data().id;
                const ed = edges.find(ed => ed.data.id === edgeId);
                if (ed) {
                    if (ed.data.source.startsWith("l2sw")) DeleteJob(ed.data.source);
                    if (ed.data.target.startsWith("l2sw")) DeleteJob(ed.data.target);
                    DeleteEdge(edgeId);
                }
            });

            clearSelection();
            refreshGraphAfterMutation(cy);
        }

        // Ctrl+Z: undo
        if (e.keyCode == 90 && e.ctrlKey) {
            clearSelection();
            RestoreNetworkObject();
            refreshGraphAfterMutation(cy);
        }

        // Ctrl+A: select all
        if (e.keyCode == 65 && e.ctrlKey) {
            e.preventDefault();
            cy.elements().select();
            updateConfigPanelForSelection(cy);
        }

        // Escape: deselect all
        if (e.keyCode == 27) {
            cy.elements().unselect();
            clearSelection();
        }

        // Ctrl+C: copy selected elements
        if (e.keyCode == 67 && e.ctrlKey && !e.shiftKey) {
            const selected = cy.elements(':selected');
            if (selected.length === 0) return;

            const payload = buildClipboardPayload(cy);
            if (!payload) return;

            // Save to internal clipboard as fallback
            internalClipboard = JSON.parse(JSON.stringify(payload));

            // Try system clipboard
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(JSON.stringify(payload)).then(function() {
                    showCopyFeedback();
                }).catch(function() {
                    showCopyFeedback();
                });
            } else {
                showCopyFeedback();
            }
        }

        // Ctrl+V: paste from clipboard
        if (e.keyCode == 86 && e.ctrlKey && !e.shiftKey) {
            e.preventDefault();

            const doPaste = function(data) {
                let clipboardData;
                try {
                    clipboardData = (typeof data === 'string') ? JSON.parse(data) : data;
                } catch (err) {
                    return;
                }
                if (!clipboardData || !clipboardData.miminet_clipboard) return;
                pasteClipboardData(JSON.parse(JSON.stringify(clipboardData)));
            };

            // Try system clipboard first, fall back to internal
            if (navigator.clipboard && navigator.clipboard.readText) {
                navigator.clipboard.readText().then(function(text) {
                    doPaste(text);
                }).catch(function() {
                    if (internalClipboard) {
                        doPaste(internalClipboard);
                    }
                });
            } else if (internalClipboard) {
                doPaste(internalClipboard);
            }
        }

    });

    // Track mouse position for paste-at-cursor
    cy.on('mousemove', function(evt) {
        lastMousePosition = evt.position;
    });

    // Initialize grid
    initGrid(cy);
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
        cy = createCytoscapeInstance(network_scheme_id, {});

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
    
    // Initialize grid
    initGrid(cy);
    
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
        cy = createCytoscapeInstance("network_scheme_shared", { autounselectify: true });

        global_cy = cy;
    }

    cy.autounselectify(true);

    cy.minZoom(0.5);
    cy.maxZoom(2);

    cy.add(nodes);
    cy.add(edges);

    // Click on object (shared/read-only mode)
    cy.on('click', function (evt) {

        let evtTarget = evt.target;
        if (evtTarget === cy) {
            clearSelection();
            return;
        }

        if (evtTarget.group() === 'edges'){
            selected_edge_id = evtTarget.data().id;
            ShowEdgeConfig(selected_edge_id, 1);
            selecteed_node_id = 0;
            return;
        }

        let n = nodes.find(n => n.data.id === evtTarget.id());
        if (!n) return;

        selecteed_node_id = n.data.id;
        selected_edge_id = 0;
        showConfigForNode(n, 1);
    });
    
    // Initialize grid
    initGrid(cy);
}

const DrawIndexGraphStatic = function(nodes, edges, container_id, graph_network_zoom,
                                    graph_network_pan_x, graph_network_pan_y)
{

    let index_cy = createCytoscapeInstance(container_id, {
        zoom: graph_network_zoom,
        pan_x: graph_network_pan_x,
        pan_y: graph_network_pan_y,
    });

    index_cy.autounselectify(false);

    index_cy.add(nodes);
    index_cy.add(edges);
    index_cy.panningEnabled(false);

    index_cy.nodes().ungrabify();
    return index_cy;
}
