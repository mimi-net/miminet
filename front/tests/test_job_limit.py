import pytest
from conftest import MiminetTester
from utils.networks import NodeType, MiminetTestNetwork
from utils.locators import Location


class TestJobLimit:
    """Tests for job limit functionality (max 30 jobs per network)."""

    def test_add_30_jobs_and_block_31st(self, selenium: MiminetTester):
        """Test that we can add 30 jobs and 31st is blocked with correct error message."""
        network = MiminetTestNetwork(selenium)

        host1_id = network.add_node(NodeType.Host)
        host2_id = network.add_node(NodeType.Host)
        network.add_edge(host1_id, host2_id)

        config1 = network.open_node_config(host1_id)
        config1.fill_link("192.168.1.1", 24)
        config1.submit()

        config2 = network.open_node_config(host2_id)
        config2.fill_link("192.168.1.2", 24)
        config2.submit()

        # Add all 30 jobs in one batch to host1
        config1 = network.open_node_config(host1_id)
        for i in range(30):
            config1.add_jobs(
                1,
                {
                    Location.Network.ConfigPanel.Host.Job.PING_FIELD.selector: "192.168.1.2"
                },
            )
        config1.submit()

        assert len(network.jobs) == 30, f"Expected 30 jobs, but got {len(network.jobs)}"

        # Try to add 31st job - should fail with informative error
        config1 = network.open_node_config(host1_id)
        config1.add_jobs(
            1,
            {Location.Network.ConfigPanel.Host.Job.PING_FIELD.selector: "192.168.1.2"},
        )

        try:
            config1.submit()
            pytest.fail("Should have raised exception about limit")
        except Exception as e:
            error_message = str(e)
            # Check error message quality
            assert "лимит" in error_message.lower(), "Error should mention limit"
            assert "30" in error_message, "Error should mention the limit number (30)"
            assert (
                "команд" in error_message.lower()
            ), "Error should mention 'команд' (commands)"

        network.delete()

    def test_limit_across_multiple_devices(self, selenium: MiminetTester):
        """Test that job limit is counted across all devices (hosts and routers) in the network."""
        network = MiminetTestNetwork(selenium)

        router_id = network.add_node(NodeType.Router)
        host1_id = network.add_node(NodeType.Host)
        host2_id = network.add_node(NodeType.Host)

        network.add_edge(router_id, host1_id)
        network.add_edge(router_id, host2_id)

        # Configure router
        config_router = network.open_node_config(router_id)
        config_router.fill_link("10.0.1.1", 24, 0)
        config_router.fill_link("10.0.2.1", 24, 1)
        config_router.submit()

        # Configure hosts
        config_host1 = network.open_node_config(host1_id)
        config_host1.fill_link("10.0.1.2", 24)
        config_host1.submit()

        config_host2 = network.open_node_config(host2_id)
        config_host2.fill_link("10.0.2.2", 24)
        config_host2.submit()

        # Add 15 jobs to router
        config_router = network.open_node_config(router_id)
        for i in range(15):
            config_router.add_jobs(
                1,
                {
                    Location.Network.ConfigPanel.Router.Job.PING_FIELD.selector: "10.0.1.2"
                },
            )
        config_router.submit()

        # Add 10 jobs to host1
        config_host1 = network.open_node_config(host1_id)
        for i in range(10):
            config_host1.add_jobs(
                1,
                {Location.Network.ConfigPanel.Host.Job.PING_FIELD.selector: "10.0.1.1"},
            )
        config_host1.submit()

        # Add 5 jobs to host2 (total 30)
        config_host2 = network.open_node_config(host2_id)
        for i in range(5):
            config_host2.add_jobs(
                1,
                {Location.Network.ConfigPanel.Host.Job.PING_FIELD.selector: "10.0.2.1"},
            )
        config_host2.submit()

        assert (
            len(network.jobs) == 30
        ), f"Expected 30 jobs across all devices, but got {len(network.jobs)}"

        # Try to add 31st job to any device - should fail
        config_host2 = network.open_node_config(host2_id)
        config_host2.add_jobs(
            1,
            {Location.Network.ConfigPanel.Host.Job.PING_FIELD.selector: "10.0.2.1"},
        )

        try:
            config_host2.submit()
            pytest.fail("Expected limit error when adding 31st job")
        except Exception as e:
            assert "30" in str(e), f"Error should mention limit of 30, got: {e}"

        network.delete()

    def test_can_add_job_after_deletion(self, selenium: MiminetTester):
        """Test that after deleting a job from network with 30 jobs, we can add a new one."""
        network = MiminetTestNetwork(selenium)

        host1_id = network.add_node(NodeType.Host)
        host2_id = network.add_node(NodeType.Host)
        network.add_edge(host1_id, host2_id)

        config1 = network.open_node_config(host1_id)
        config1.fill_link("192.168.1.1", 24)
        config1.submit()

        config2 = network.open_node_config(host2_id)
        config2.fill_link("192.168.1.2", 24)
        config2.submit()

        # Add 30 jobs in one batch
        config1 = network.open_node_config(host1_id)
        for i in range(30):
            config1.add_jobs(
                1,
                {
                    Location.Network.ConfigPanel.Host.Job.PING_FIELD.selector: "192.168.1.2"
                },
            )
        config1.submit()

        assert (
            len(network.jobs) == 30
        ), f"Expected 30 jobs initially, but got {len(network.jobs)}"

        # Delete one job via API
        job_id_to_delete = network.jobs[0]["id"]

        delete_result = selenium.execute_script(
            f"""
            return new Promise((resolve) => {{
                $.ajax({{
                    type: 'POST',
                    url: '/host/delete_job',
                    data: {{
                        id: '{job_id_to_delete}',
                        guid: network_guid
                    }},
                    encode: true,
                    success: function(data, textStatus, xhr) {{
                        if (xhr.status === 200) {{
                            jobs = data.jobs;
                            resolve({{ success: true, jobs_count: jobs.length }});
                        }} else {{
                            resolve({{ success: false }});
                        }}
                    }},
                    error: function() {{
                        resolve({{ success: false }});
                    }}
                }});
            }});
        """
        )
        assert delete_result["success"], "Failed to delete job"
        assert (
            len(network.jobs) == 29
        ), f"Expected 29 jobs after deletion, but got {len(network.jobs)}"

        # Add a new job - should succeed
        config1 = network.open_node_config(host1_id)
        config1.add_jobs(
            1,
            {Location.Network.ConfigPanel.Host.Job.PING_FIELD.selector: "192.168.1.2"},
        )
        config1.submit()

        assert (
            len(network.jobs) == 30
        ), f"Expected 30 jobs after adding new one, but got {len(network.jobs)}"

        network.delete()
