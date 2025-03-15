"""Classes for deserializing a Miminet network"""

from dataclasses import dataclass
from typing import Union, Optional


@dataclass
class NodeData:
    """
    Represents data associated with a network node.

    Attributes:
        id (str): Unique identifier for the node.
        label (str): Human-readable label for the node.
    """

    id: str
    label: str


@dataclass
class NodeConfig:
    """
    Configuration settings for a network node.

    Attributes:
        label (str): Label for the node (e.g., "l2sw1").
        type (str): Node type (e.g., "l2_switch").
        stp (int): 1 if spanning tree protocol (STP) is enabled; 2 if rapid spanning tree protocol (RSTP) is enabled; 0 otherwise.
        priority (Optional[int]): stp or rstp priority
        default_gw (str): Default gateway for the node.
    """

    label: str = ""
    type: str = ""
    stp: int = 0
    priority: Optional[int] = None
    default_gw: str = ""


@dataclass
class NodeInterface:
    """
    Represents an interface of a network node.

    Attributes:
        connect (str): Label of the node the interface connects to (e.g., "l2sw1").
        id (str): Unique identifier for the interface (e.g., "l2sw1_1").
        name (str): Name of the interface (e.g., "l2sw1_1").
        ip (str): IP address (e.g., "10.0.0.1").
        netmask (int): Netmask.
        vlan (Union[int, List[int], None]): VLAN ID or list of VLANs.
        type_connection (Optional[int]): Type of connection (0 - Access, 1 - Trunk).

    """

    connect: str
    id: str
    name: str = ""
    ip: str = ""
    netmask: int = 0
    vlan: Union[int, list[int], None] = None
    type_connection: Optional[int] = None
    vxlan_vni: Optional[int] = None
    vxlan_connection_type: Optional[int] = None
    vxlan_vni_to_target_ip: Optional[list[list[str]]] = None


@dataclass
class NodePosition:
    """
    Represents the graphical position of a node.

    Attributes:
        x (float): X-coordinate.
        y (float): Y-coordinate.
    """

    x: float
    y: float


@dataclass
class Node:
    """
    Represents a network node with its configuration, data, interfaces, position, and classes.

    Attributes:
        config (NodeConfig): Configuration settings.
        data (NodeData): Data associated.
        interface (list[NodeInterface]): List of interfaces.
        position (NodePosition): Graphical position.
        classes (list[str]): Node classes (e.g., ["l2_switch"]).
    """

    config: NodeConfig
    data: NodeData
    interface: list[NodeInterface]
    classes: list[str]
    position: NodePosition


@dataclass
class EdgeData:
    """Represents data associated with an edge connecting two nodes.

    Args:
        id (str): Unique identifier for the edge.
        source (str) : Label of the source node.(e.g., "host_2")
        target (str): Label of the target node. (e.g., "l1hub1")

    """

    id: str
    source: str
    target: str


@dataclass
class Edge:
    """
    Represents an edge connecting two nodes.

    Attributes:
        data (EdgeData): Data associated with the edge.
    """

    data: EdgeData


@dataclass
class Job:
    """
    Represents a job to be executed on the network (e.g., ping).

    Args:
        id (str): str job id
        level (int): job level
        job_id (int): int job id (for execute)
        host_id (str): host id for job executing (e.g., host_1)
        arg_1 (str): parameter for job executing (e.g., example, ip, port, netmask, ...)
        arg_2 (str): parameter for job executing
        arg_3 (str): parameter for job executing
        arg_4 (str): parameter for job executing
    """

    id: str
    level: int
    job_id: int
    host_id: str
    print_cmd: str
    arg_1: str | int = ""
    arg_2: str | int = ""
    arg_3: str | int = ""
    arg_4: str | int = ""


@dataclass
class NetworkConfig:
    """
    Configuration settings for the overall network visualization.

    Args:
        zoom (float): Zoom level for the network view.
        pan_x (float): Horizontal pan offset for the view.
        pan_y (float): Vertical pan offset for the view.

    """

    zoom: float
    pan_x: float
    pan_y: float


@dataclass
class Network:
    """
    Represents the complete Mininet network with nodes, edges, jobs, configuration, and network traffic data.

    Args:
        nodes (list[Node]): list of network nodes.
        edges (list[Edge]): list of connections between nodes.
        jobs (list[Job]): List of jobs to be executed on the network.
        config (NetworkConfig): Network visualization configuration.
        packets (str): packets
        pcap (list[str]): List of PCAP files containing network traffic data.

    """

    nodes: list[Node]
    edges: list[Edge]
    jobs: list[Job]
    config: NetworkConfig
    pcap: list[str] | None
    packets: str = ""
