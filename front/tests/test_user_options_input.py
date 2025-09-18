import pytest
from utils.networks import NodeType, MiminetTestNetwork
from utils.locators import Location
from conftest import MiminetTester


class TestPingOptionsFilter:
    @pytest.fixture(scope="class")
    def network(self, selenium: MiminetTester):
        network = MiminetTestNetwork(selenium)

        host1_node = network.add_node(NodeType.Host)
        host2_node = network.add_node(NodeType.Host)
        network.add_edge(host1_node, host2_node)

        config0 = network.open_node_config(host1_node)
        config0.fill_link("10.0.0.1", 24)

        config1 = network.open_node_config(host2_node)
        config1.fill_link("10.0.0.2", 24)
        config1.submit()

        yield network
        network.delete()

    @pytest.mark.parametrize(
        "options_input,expected_args",
        [
            ("-c 5 -t 10 ; rm -rf /", "-c 5 -t 10"),
            ("-s 1200 -b --badflag", "-s 1200 -b"),
            ("echo test && -i 3", "-i 3"),
            ("-c 10 -c 56 -c 12 -b -b -b -i 3 -i 10", "-c 10 -b -i 3"),
            ("-c -c -c -c 5 -i -b", "-c 5 -b"),
            ("-c -x -c 11 -c 5", "-c 5"),
        ],
    )
    def test_ping_options_whitelist(
        self,
        network: MiminetTestNetwork,
        options_input,
        expected_args,
    ):
        host1_node = network.nodes[0]

        config = network.open_node_config(host1_node)
        config.add_jobs(
            2,
            {
                Location.Network.ConfigPanel.Host.Job.PING_OPTION_FIELD.selector: options_input,
                Location.Network.ConfigPanel.Host.Job.PING_OPTION_IP_FIELD.selector: "10.0.0.2",
            },
        )
        config.submit()

        last_job = network.jobs[-1]
        filtered_args = last_job["arg_1"].strip()
        assert filtered_args == expected_args
        assert last_job["arg_2"] == "10.0.0.2"

    def test_ping_options_blacklist(self, network: MiminetTestNetwork):
        host1_node = network.nodes[0]

        config = network.open_node_config(host1_node)

        with pytest.raises(Exception) as exc_info:
            config.add_jobs(
                2,
                {
                    Location.Network.ConfigPanel.Host.Job.PING_OPTION_FIELD.selector: "; rm -rf /",
                    Location.Network.ConfigPanel.Host.Job.PING_OPTION_IP_FIELD.selector: "10.0.0.2",
                },
            )
            config.submit()

        assert "Неверно указаны опции" in str(exc_info.value)
