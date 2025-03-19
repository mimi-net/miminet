"""
    This module provides functions necessary to check the correctness of the networks built in tests.
    You can compare nodes, edges and jobs to convince that what you have done is right.
"""

import re


class TestNetworkComparator:
    """Utility class for comparing nodes, edges, and jobs in your test networks."""

    def __compare_lists(list_a, list_b, item_name):
        if not list_a or not list_b:
            raise ValueError(f"{item_name.capitalize()} for comparison can't be empty.")
        if len(list_a) != len(list_b):
            raise ValueError(
                f"Number of {item_name} mismatch: Expected {len(list_a)}, got {len(list_b)}."
            )

    def __normalize_print_cmd(cmd):
        return re.sub(r"iface_\d+", "", cmd).replace("\\n", "\n")

    def compare_nodes(nodes_a, nodes_b) -> bool:
        TestNetworkComparator.__compare_lists(nodes_a, nodes_b, "nodes")

        for i, (node_a, node_b) in enumerate(zip(nodes_a, nodes_b)):
            if node_a["classes"] != node_b["classes"]:
                raise ValueError(f"Node {i}: Classes mismatch.")

            TestNetworkComparator.__compare_lists(
                node_a["interface"], node_b["interface"], f"Node {i} interfaces"
            )

            for j, (iface_a, iface_b) in enumerate(
                zip(node_a["interface"], node_b["interface"])
            ):
                for key in ("ip", "netmask"):
                    if key in iface_a and iface_a[key] != iface_b.get(key):
                        raise ValueError(
                            f"Node {i}, Interface {j}: {key.capitalize()} mismatch."
                        )

            if node_a["data"] != node_b["data"]:
                raise ValueError(f"Node {i}: Data mismatch.")

        return True

    def compare_edges(edges_a, edges_b) -> bool:
        TestNetworkComparator.__compare_lists(edges_a, edges_b, "edges")

        for i, (edge_a, edge_b) in enumerate(zip(edges_a, edges_b)):
            try:
                if edge_a["data"]["source"] != edge_b["data"]["source"]:
                    raise ValueError(f"Edge {i}: Source mismatch.")
                if edge_a["data"]["target"] != edge_b["data"]["target"]:
                    raise ValueError(f"Edge {i}: Target mismatch.")
            except KeyError as e:
                raise ValueError(f"Edge {i}: Missing key {e} in edge data.")

        return True

    def compare_jobs(jobs_a, jobs_b) -> bool:
        TestNetworkComparator.__compare_lists(jobs_a, jobs_b, "jobs")
        normalize = TestNetworkComparator.__normalize_print_cmd

        for i, (job_a, job_b) in enumerate(zip(jobs_a, jobs_b)):
            if normalize(job_a["print_cmd"]) != normalize(job_b["print_cmd"]):
                raise ValueError(f"Job {i}: 'print_cmd' mismatch.")
            for key in ("job_id", "host_id"):
                if job_a[key] != job_b[key]:
                    raise ValueError(f"Job {i}: '{key}' mismatch.")

        return True
