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
        })

        .selector('node:selected')
        .css({
            'overlay-color': '#2176FF',
            'overlay-padding': 6,
            'overlay-opacity': 0.2
        })

        .selector('edge:selected')
        .css({
            'overlay-color': '#2176FF',
            'overlay-padding': 4,
            'overlay-opacity': 0.2
        })

        .selector('.copy-flash')
        .css({
            'overlay-color': '#28a745',
            'overlay-opacity': 0.3,
            'overlay-padding': 8
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
