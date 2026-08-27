"""Capture file paths written by mimidump.

mimidump writes ``capture_{interface}.pcapng`` (bidirectional) and
``capture_{interface}_out.pcapng`` (outbound) into the node working directory
(``/tmp`` for the emulation). All producers and consumers of these paths go
through the helpers here so the layout stays in a single place.
"""


def capture_paths(iface_name: str) -> tuple[str, str]:
    """Return (bidirectional, outbound) pcapng paths for an interface."""
    return (
        f"/tmp/capture_{iface_name}.pcapng",
        f"/tmp/capture_{iface_name}_out.pcapng",
    )


def capture_out_path(iface_name: str) -> str:
    """Return the outbound pcapng path for an interface."""
    return f"/tmp/capture_{iface_name}_out.pcapng"


def iter_capture_out_files(interfaces):
    """Yield (interface_name, outbound pcapng path) for every link endpoint."""
    for link1, link2, *_ in interfaces:
        yield link1, capture_out_path(link1)
        yield link2, capture_out_path(link2)
