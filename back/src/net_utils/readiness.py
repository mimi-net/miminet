"""Pure helpers for the network-readiness gate.

The readiness gate (``MiminetNetwork.__wait_until_ready``) walks the link
endpoints of a topology and inspects the packet capture attached to each
interface. The endpoint-walking scaffold used to be duplicated across the
capture-liveness probe and the capture-restart path; it lives here so the
decision logic stays in one testable place.
"""


def iter_capture_endpoints(interfaces, get_intf):
    """Yield ``(node_name, iface_name, intf, captures)`` for every link endpoint
    that resolves to an interface object.

    ``interfaces`` is the topology's list of ``(link1, link2, edge_id,
    edge_source, edge_target, ...)`` tuples, where ``linkN`` is the interface
    name on the ``edge_*`` node. ``get_intf(node_name, iface_name)`` returns
    the interface object (or ``None``); lookups that raise ``KeyError`` /
    ``AttributeError`` (node or interface no longer present) are skipped.
    """
    for link1, link2, _edge_id, edge_source, edge_target, *_rest in interfaces:
        for iface_name, node_name in ((link1, edge_source), (link2, edge_target)):
            try:
                intf = get_intf(node_name, iface_name)
            except (KeyError, AttributeError):
                continue
            if intf is None:
                continue
            yield node_name, iface_name, intf, intf.get("captures", [])
