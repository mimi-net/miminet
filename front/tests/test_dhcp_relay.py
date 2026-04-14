import pytest
from conftest import MiminetTester
from utils.networks import NodeType, MiminetTestNetwork
from utils.locators import Location
from utils.checkers import TestNetworkComparator

class TestDHCPRelay:
    @pytest.fixture(scope="class")
    def network(self, selenium: MiminetTester):
        network = MiminetTestNetwork(selenium)

        # nodes
        network.add_node(NodeType.Host, 250, 275)  # host
        network.add_node(NodeType.Switch, 250, 175)  # switch 1
        network.add_node(NodeType.Router, 350, 75) # router
        network.add_node(NodeType.Switch, 400, 175)  # switch 2
        network.add_node(NodeType.Server, 400, 275)  # server

        # edges
        network.add_edge(0, 1)  # host -> switch 1
        network.add_edge(1, 2)  # switch 1 -> router
        network.add_edge(2, 3)  # router -> switch 2
        network.add_edge(3, 4)  # switch 2 -> server

        # configure host
        host_iface = network.nodes[0]["interface"][0]["id"]
        host_config = network.open_node_config(0)
        host_config.add_jobs(
            108,
            {Location.Network.ConfigPanel.Host.Job.DHCLIENT_INTF.selector: host_iface},
        )
        host_config.submit()

        # configure router
        router_iface = network.nodes[2]["interface"][0]["id"]
        router_config = network.open_node_config(2)
        router_config.fill_link("172.16.10.3", 24)
        router_config.fill_link("192.168.10.3", 24, 1)
        router_config.add_jobs(
            204,
            {
                Location.Network.ConfigPanel.Router.Job.DHCP_RELAY_IP_INPUT_FIELD.selector: "192.168.10.2",
                Location.Network.ConfigPanel.Router.Job.ADD_ROUTE_MASK_FIELD.selector: "24",
                Location.Network.ConfigPanel.Router.Job.DHCP_RELAY_SELECT_IFACE_FIELD: router_iface,
            },
        )
        router_config.submit()

        # config server
        server_iface = network.nodes[4]["interface"][0]["id"]
        server_config = network.open_node_config(4)
        server_config.fill_link("192.168.10.2", 24)
        server_config.add_jobs(
            203,
            {
                Location.Network.ConfigPanel.Server.Job.DHCP_IP_RANGE_START_FIELD.selector: "172.16.10.10",
                Location.Network.ConfigPanel.Server.Job.DHCP_IP_RANGE_END_FIELD.selector: "172.16.10.100",
                Location.Network.ConfigPanel.Server.Job.DHCP_MASK_FIELD.selector: "24",
                Location.Network.ConfigPanel.Server.Job.DHCP_IP_GW_FIELD.selector: "172.16.10.3",
                Location.Network.ConfigPanel.Server.Job.DHCP_INTF.selector: server_iface,
            },
        )
        server_config.submit()

        yield network

        network.delete()
    
    def test_dhcp(self, selenium: MiminetTester, network: MiminetTestNetwork):
        assert TestNetworkComparator.compare_nodes(network.nodes, self.JSON_NODES)
        assert TestNetworkComparator.compare_edges(network.edges, self.JSON_EDGES)
        assert TestNetworkComparator.compare_jobs(network.jobs, self.JSON_JOBS)

    JSON_NODES = [
        {
            "data":{
                "id":"host_1",
                "label":"host_1"
            },
            "position":{
                "x":250,
                "y":275
            },
            "classes":[
                "host"
            ],
            "config":{
                "type":"host",
                "label":"host_1",
                "default_gw":""
            },
            "interface":[
                {
                "id":"iface_61426530",
                "name":"iface_61426530",
                "connect":"edge_mnysboa63sl7masz29i"
                }
            ]
        },
        {
            "data":{
                "id":"l2sw1",
                "label":"l2sw1"
            },
            "position":{
                "x":250,
                "y":175
            },
            "classes":[
                "l2_switch"
            ],
            "config":{
                "type":"l2_switch",
                "label":"l2sw1",
                "stp":0
            },
            "interface":[
                {
                "id":"l2sw1_1",
                "name":"l2sw1_1",
                "connect":"edge_mnysboa63sl7masz29i",
                "vlan":None,
                "type_connection":None
                },
                {
                "id":"l2sw1_2",
                "name":"l2sw1_2",
                "connect":"edge_mnysbpcfq1uwnl5unw",
                "vlan":None,
                "type_connection":None
                }
            ]
        },
        {
            "data":{
                "id":"router_1",
                "label":"router_1"
            },
            "position":{
                "x":350,
                "y":75
            },
            "classes":[
                "l3_router"
            ],
            "config":{
                "type":"router",
                "label":"router_1",
                "default_gw":""
            },
            "interface":[
                {
                "id":"iface_73510361",
                "name":"iface_73510361",
                "connect":"edge_mnysbpcfq1uwnl5unw",
                "ip":"172.16.10.3",
                "netmask":24
                },
                {
                "id":"iface_37513030",
                "name":"iface_37513030",
                "connect":"edge_mnysbqjka0cbjig1jb7",
                "ip":"192.168.10.3",
                "netmask":24
                }
            ]
        },
        {
            "data":{
                "id":"l2sw2",
                "label":"l2sw2"
            },
            "position":{
                "x":400,
                "y":175
            },
            "classes":[
                "l2_switch"
            ],
            "config":{
                "type":"l2_switch",
                "label":"l2sw2",
                "stp":0
            },
            "interface":[
                {
                "id":"l2sw2_1",
                "name":"l2sw2_1",
                "connect":"edge_mnysbqjka0cbjig1jb7",
                "vlan":None,
                "type_connection":None
                },
                {
                "id":"l2sw2_2",
                "name":"l2sw2_2",
                "connect":"edge_mnysbrok5nl01pdvoe3",
                "vlan":None,
                "type_connection":None
                }
            ]
        },
        {
            "data":{
                "id":"server_1",
                "label":"server_1"
            },
            "position":{
                "x":400,
                "y":275
            },
            "classes":[
                "server"
            ],
            "config":{
                "type":"server",
                "label":"server_1",
                "default_gw":""
            },
            "interface":[
                {
                "id":"iface_84271537",
                "name":"iface_84271537",
                "connect":"edge_mnysbrok5nl01pdvoe3",
                "ip":"192.168.10.2",
                "netmask":24
                }
            ]
        }
    ]
    JSON_EDGES = [
        {
            "data":{
                "id":"edge_mnysboa63sl7masz29i",
                "source":"host_1",
                "target":"l2sw1",
                "loss_percentage":0,
                "duplicate_percentage":0
            }
        },
        {
            "data":{
                "id":"edge_mnysbpcfq1uwnl5unw",
                "source":"l2sw1",
                "target":"router_1",
                "loss_percentage":0,
                "duplicate_percentage":0
            }
        },
        {
            "data":{
                "id":"edge_mnysbqjka0cbjig1jb7",
                "source":"router_1",
                "target":"l2sw2",
                "loss_percentage":0,
                "duplicate_percentage":0
            }
        },
        {
            "data":{
                "id":"edge_mnysbrok5nl01pdvoe3",
                "source":"l2sw2",
                "target":"server_1",
                "loss_percentage":0,
                "duplicate_percentage":0
            }
        }
    ]
    JSON_JOBS = [  
        {
            "id":"6a39abbd1e7246cdb17f73544745c73f",
            "job_id":108,
            "print_cmd":"dhcp client",
            "arg_1":"iface_61426530",
            "level":0,
            "host_id":"host_1"
        },
        {
            "id":"e796339025e747ccb06421d7c42d897e",
            "job_id":204,
            "print_cmd":"dhcp-helper -s 192.168.10.2 -i iface_73510361",
            "arg_1":"192.168.10.2",
            "arg_2":"24",
            "arg_3":"iface_73510361",
            "level":1,
            "host_id":"router_1"
        },
        {
            "id":"64ef30fbc1ea4322a6c85b52739322d8",
            "job_id":203,
            "print_cmd":"dhcp ip range: 172.16.10.10,172.16.10.100/24 gw:172.16.10.3",
            "arg_1":"172.16.10.10",
            "arg_2":"172.16.10.100",
            "arg_3":"24",
            "arg_4":"172.16.10.3",
            "arg_5":"iface_84271537",
            "level":2,
            "host_id":"server_1"
        }
    ]
