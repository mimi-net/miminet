const uid = function(){
    return Date.now().toString(36) + Math.random().toString(36).substr(2);
}

const HostUid = function(){
    return "host_" + uid();
}

const l2SwitchUid = function(){
    return "l2_switch_" + uid();
}

const EdgeUid = function(){
    return "edge_" + uid();
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
      return ele.data('label') || ele.data('id');
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
          'text-halign': 'center',
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

    let eh = cy.edgehandles( defaults );

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

        if (n.config.type === 'host'){

            let host_label = n.config.label;
            host_label = host_label || n.data.id;

            $('#hostConfigModalLabel').text('Конфигурация ' + host_label);
            $('#hostConfigModal').modal('toggle');
        }
    });

    // Turn on/off eh.enableDrawMode();
    $(document).on('keyup keydown', function(e){

    if (shifted != e.shiftKey)
    {
        shifted = e.shiftKey;

        if (shifted)
        {
            eh.enableDrawMode();
            console.log("Turn on drawmode");
        } else {
             eh.disableDrawMode();
            console.log("Turn off drawmode");
        }

    }
});
}