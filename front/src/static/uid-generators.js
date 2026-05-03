const uid = function(){
    return Date.now().toString(36) + Math.random().toString(36).substr(2);
}

const nextAvailableId = function(prefix, fallbackPrefix) {
    for (let num = 1; num < 100; num++) {
        let candidate = prefix + num;
        if (!nodes.find(n => n.data.id === candidate)) {
            return candidate;
        }
    }
    return (fallbackPrefix || prefix) + uid();
}

const HostUid = function(){ return nextAvailableId("host_"); }
const RouterUid = function(){ return nextAvailableId("router_"); }
const ServerUid = function(){ return nextAvailableId("server_"); }
const l1HubUid = function(){ return nextAvailableId("l1hub", "hub_"); }
const l2SwitchUid = function(){ return nextAvailableId("l2sw", "sw_"); }

const nextAvailablePortId = function(nodeId) {
    let node = nodes.find(n => n.data.id === nodeId);
    if (!node) return -1;

    for (let num = 1; num < 128; num++) {
        let candidate = node.data.id + "_" + num;
        if (!node.interface.find(i => i.id === candidate)) {
            return candidate;
        }
    }
}

const l2SwitchPortUid = function(switch_id){ return nextAvailablePortId(switch_id); }
const l1HubPortUid = function(hub_id){ return nextAvailablePortId(hub_id); }

const PacketUid = function(){ return "pkt_" + uid(); }
const EdgeUid = function(){ return "edge_" + uid(); }
const InterfaceUid = function(){ return "iface_" + Math.random().toString(9).substring(2, 10); }
