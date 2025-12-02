import pytest
import time
from conftest import MiminetTester
from utils.networks import NodeType, MiminetTestNetwork
from utils.locators import Location
from selenium.webdriver.common.by import By


class TestJobEdit:
    """Tests for job editing functionality (edit mode)."""

    def test_host_edit_ping_job(self, selenium: MiminetTester):
        """Test editing a ping job on a host."""
        network = MiminetTestNetwork(selenium)

        host1_id = network.add_node(NodeType.Host)
        host2_id = network.add_node(NodeType.Host)
        network.add_edge(host1_id, host2_id)

        # Configure hosts
        config1 = network.open_node_config(host1_id)
        config1.fill_link("192.168.1.1", 24)
        config1.submit()

        config2 = network.open_node_config(host2_id)
        config2.fill_link("192.168.1.2", 24)
        config2.submit()

        # Add initial ping job
        config1 = network.open_node_config(host1_id)
        config1.add_jobs(
            1,
            {Location.Network.ConfigPanel.Host.Job.PING_FIELD.selector: "192.168.1.2"},
        )
        config1.submit()

        initial_jobs_count = len(network.jobs)
        assert initial_jobs_count == 1, f"Expected 1 job, got {initial_jobs_count}"
        initial_job_id = network.jobs[0]["id"]

        # Open config and click edit button for the job
        config1 = network.open_node_config(host1_id)
        edit_button = selenium.find_element(
            By.CSS_SELECTOR, f"#config_host_job_edit_{initial_job_id}"
        )
        edit_button.click()

        time.sleep(0.3)

        # Check that job field is pre-filled with original value
        ping_field = selenium.find_element(
            By.CSS_SELECTOR, Location.Network.ConfigPanel.Host.Job.PING_FIELD.selector
        )
        assert (
            ping_field.get_attribute("value") == "192.168.1.2"
        ), "Original ping target should be pre-filled"

        # Modify the job
        ping_field.clear()
        ping_field.send_keys("192.168.1.100")

        # Submit the changes
        config1.submit()

        # Verify job was updated, not duplicated
        final_jobs_count = len(network.jobs)
        assert (
            final_jobs_count == 1
        ), f"Job should be updated, not duplicated. Got {final_jobs_count} jobs"

        # Verify the new value is saved
        updated_job = network.jobs[0]
        assert (
            updated_job["arg_1"] == "192.168.1.100"
        ), f"Job should have new IP, got: {updated_job['arg_1']}"

        network.delete()

    def test_edit_job_preserves_job_limit(self, selenium: MiminetTester):
        """Test that editing a job doesn't count against the 30-job limit."""
        network = MiminetTestNetwork(selenium)

        host1_id = network.add_node(NodeType.Host)
        host2_id = network.add_node(NodeType.Host)
        network.add_edge(host1_id, host2_id)

        # Configure hosts
        config1 = network.open_node_config(host1_id)
        config1.fill_link("192.168.5.1", 24)
        config1.submit()

        config2 = network.open_node_config(host2_id)
        config2.fill_link("192.168.5.2", 24)
        config2.submit()

        # Add 30 jobs
        config1 = network.open_node_config(host1_id)
        for i in range(30):
            config1.add_jobs(
                1,
                {
                    Location.Network.ConfigPanel.Host.Job.PING_FIELD.selector: "192.168.5.2"
                },
            )
        config1.submit()

        assert len(network.jobs) == 30, f"Expected 30 jobs, got {len(network.jobs)}"

        # Get first job info before editing
        first_job = network.jobs[0]
        first_job_id = first_job["id"]
        first_job_original_ip = first_job["arg_1"]

        # Edit one of the jobs
        config1 = network.open_node_config(host1_id)
        selenium.find_element(
            By.CSS_SELECTOR, f"#config_host_job_edit_{first_job_id}"
        ).click()

        time.sleep(0.3)

        # Modify the ping target
        ping_field = selenium.find_element(
            By.CSS_SELECTOR, Location.Network.ConfigPanel.Host.Job.PING_FIELD.selector
        )
        ping_field.clear()
        ping_field.send_keys("192.168.5.99")

        # Submit should succeed (edit doesn't count as new job)
        config1.submit()

        # Verify still 30 jobs
        assert (
            len(network.jobs) == 30
        ), f"Should still have 30 jobs after edit, got {len(network.jobs)}"

        # Verify at least one job has the new IP (jobs may be reordered)
        job_ips = [job["arg_1"] for job in network.jobs]
        assert (
            "192.168.5.99" in job_ips
        ), f"Updated IP should be in jobs list: {job_ips}"
        assert (
            first_job_original_ip not in job_ips
            or job_ips.count(first_job_original_ip) < 30
        ), "Original IP should be replaced"

        network.delete()

    def test_edit_multiple_jobs_in_sequence(self, selenium: MiminetTester):
        """Test editing multiple jobs in sequence."""
        network = MiminetTestNetwork(selenium)

        host_id = network.add_node(NodeType.Host)
        router_id = network.add_node(NodeType.Router)
        network.add_edge(host_id, router_id)

        # Configure host
        config_host = network.open_node_config(host_id)
        config_host.fill_link("10.20.30.2", 24)
        config_host.submit()

        # Configure router
        config_router = network.open_node_config(router_id)
        config_router.fill_link("10.20.30.1", 24)
        config_router.submit()

        # Add 3 ping jobs to host with different IPs
        config_host = network.open_node_config(host_id)
        for i in range(3):
            config_host.add_jobs(
                1,
                {
                    Location.Network.ConfigPanel.Host.Job.PING_FIELD.selector: f"10.20.30.{10+i}"
                },
            )
        config_host.submit()

        assert len(network.jobs) == 3, "Should have 3 jobs initially"

        # Store original job IDs
        job_ids = [job["id"] for job in network.jobs]

        # Edit first job
        config_host = network.open_node_config(host_id)
        selenium.find_element(
            By.CSS_SELECTOR, f"#config_host_job_edit_{job_ids[0]}"
        ).click()
        time.sleep(0.3)

        ping_field = selenium.find_element(
            By.CSS_SELECTOR, Location.Network.ConfigPanel.Host.Job.PING_FIELD.selector
        )
        ping_field.clear()
        ping_field.send_keys("10.20.30.100")
        config_host.submit()

        # Edit second job
        config_host = network.open_node_config(host_id)
        selenium.find_element(
            By.CSS_SELECTOR, f"#config_host_job_edit_{job_ids[1]}"
        ).click()
        time.sleep(0.3)

        ping_field = selenium.find_element(
            By.CSS_SELECTOR, Location.Network.ConfigPanel.Host.Job.PING_FIELD.selector
        )
        ping_field.clear()
        ping_field.send_keys("10.20.30.101")
        config_host.submit()

        # Verify all jobs were updated
        assert len(network.jobs) == 3, "Should still have exactly 3 jobs"

        # Verify new IPs are present
        updated_ips = [job["arg_1"] for job in network.jobs]
        assert (
            "10.20.30.100" in updated_ips
        ), f"First edited IP not found in {updated_ips}"
        assert (
            "10.20.30.101" in updated_ips
        ), f"Second edited IP not found in {updated_ips}"

        network.delete()
