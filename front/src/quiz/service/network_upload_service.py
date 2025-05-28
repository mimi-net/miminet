from typing import Dict, List, Tuple, Any
from celery_app import app
from copy import deepcopy
import json
import uuid


def create_check_task(network: dict, requirements: list[dict], session_question_id):
    """Prepare task network and send it to checking service."""

    prepared_task = prepare_task(network, requirements)
    prepared_task_json = [
        (json.dumps(net), json.dumps(req), json.dumps(mods))
        for net, req, mods in prepared_task
    ]

    # send task
    app.send_task(
        "tasks.check_task_network",
        args=[session_question_id, prepared_task_json],
        routing_key="task-checking-routing-key",
        exchange="task-checking-exchange",
        exchange_type="direct",
    )


def create_check_task_json(networks, requirements: list[dict]):
    for network in networks:
        prepared_task = prepare_task(network[0], requirements)
        prepared_task_json = [
            (json.dumps(net), json.dumps(req), json.dumps(mods), json.dumps(network[1]))
            for net, req, mods in prepared_task
        ]

        # send task
        app.send_task(
            "tasks.check_task_network",
            args=[None, prepared_task_json],
            routing_key="task-checking-routing-key",
            exchange="task-checking-exchange",
            exchange_type="direct",
        )


# Unnecessary for task checking: (ping, ping with options, TCP/UDP ping, TCP/UDP server)
EXCLUDED_JOB_IDS = (1, 2, 3, 4, 200, 201)


def prepare_task(user_network: dict, task_req: list[dict]):
    """
    Prepare task according to requirements:
    - Split task to several separate network schemas,
    - Modify these schemas.

    Args:
        user_network (dict): Network schema created by user.
        task_req (dict): Task requirements (description of what we need to check).

    Returns:
        List[Tuple]: List of tuples (network schema, requirements).
    """

    cleaned_network = clean_schema(user_network)
    tasks = get_configured_tasks(cleaned_network, task_req)

    return tasks


def get_configured_tasks(schema: Dict[str, Any], scenarios: List[Dict]) -> List[Tuple]:
    """Divide single schema into several separated schemas according to requirements."""
    results: List[Tuple] = []

    for scenario in scenarios:
        modifications = scenario.get("modifications", [])

        # Every scenario generates new schema and requirements,
        # we need it in additional checks
        scenario_schema = deepcopy(schema)
        scenario_requirements = deepcopy(scenario.get("requirements", {}))

        applied_modifications = []

        for modification in modifications:
            modification_keys: List = list(modification.keys())

            if len(modification_keys) != 1:
                raise ValueError(
                    f"Incorrect requirements modification keys: {modification_keys}."
                )

            modification_name: str = modification_keys[0]
            modification_arg: Dict[str, str] = modification[modification_name]

            if modification_name == "remove_edge":
                edge_id = modification_arg.get("id")
                from_node = modification_arg.get("from")
                to_node = modification_arg.get("to")

                if edge_id:
                    edge = next(
                        (
                            e
                            for e in scenario_schema.get("edges", [])
                            if e.get("data", {}).get("id") == edge_id
                        ),
                        None,
                    )

                    if edge:
                        from_node = edge["data"].get("source", "unknown")
                        to_node = edge["data"].get("target", "unknown")
                        applied_modifications.append(
                            {
                                "remove_edge": {
                                    "id": edge_id or "unknown",
                                    "between": f"{from_node} ↔ {to_node}",
                                }
                            }
                        )

                    scenario_schema["edges"] = [
                        edge
                        for edge in scenario_schema.get("edges", [])
                        if edge.get("data", {}).get("id") != edge_id
                    ]

                elif from_node and to_node:
                    matching_edges = [
                        edge
                        for edge in scenario_schema.get("edges", [])
                        if (
                            edge.get("data", {}).get("source") == from_node
                            and edge.get("data", {}).get("target") == to_node
                        )
                        or (
                            edge.get("data", {}).get("source") == to_node
                            and edge.get("data", {}).get("target") == from_node
                        )
                    ]

                    if not matching_edges:
                        raise ValueError(
                            f"No edge found between '{from_node}' and '{to_node}'."
                        )

                    edge = matching_edges[0]
                    edge_id = edge["data"].get("id")

                    applied_modifications.append(
                        {
                            "remove_edge": {
                                "id": edge_id or "unknown",
                                "between": f"{from_node} ↔ {to_node}",
                            }
                        }
                    )

                    scenario_schema["edges"] = [
                        e
                        for e in scenario_schema.get("edges", [])
                        if e.get("data", {}).get("id") != edge_id
                    ]

                else:
                    raise ValueError(
                        "Either 'id' or both 'from' and 'to' must be provided for remove_edge."
                    )

            elif modification_name == "add_ping":
                from_host_name = modification_arg.get("from")
                to_host_name = modification_arg.get("to")

                if from_host_name is None or to_host_name is None:
                    raise ValueError(
                        "'from' and 'to' must be specified for add_ping modification"
                    )

                # Find the 'to' host node
                node = next(
                    (
                        n
                        for n in scenario_schema.get("nodes", [])
                        if n.get("data", {}).get("id") == to_host_name
                    ),
                    None,
                )

                # Validate node and interface/ip availability
                if not node:
                    # No such host: skip adding ping
                    continue

                interfaces = node.get("interface") or []
                if not isinstance(interfaces, list) or len(interfaces) == 0:
                    # No interfaces configured: skip
                    continue

                first_if = interfaces[0] or {}
                to_host_ip = first_if.get("ip")
                if not to_host_ip:
                    # IP not configured: skip
                    continue

                # Add ping job
                scenario_schema.setdefault("jobs", []).append(
                    {
                        "id": uuid.uuid4().hex,
                        "job_id": 1,
                        "print_cmd": f"ping -c 1 {to_host_ip}",
                        "arg_1": to_host_ip,
                        "level": -1,
                        "host_id": from_host_name,
                    }
                )

            else:
                raise ValueError(
                    f"Unknown requirements modifier name: {modification_name}."
                )

        results.append((scenario_schema, scenario_requirements, applied_modifications))

    return results


def clean_schema(user_schema: Dict[str, Any]) -> Dict[str, Any]:
    """Remove unnecessary jobs from the user's network schema."""
    if not isinstance(user_schema, dict):
        raise TypeError("Expected user_network to be a dictionary.")

    jobs = user_schema.get("jobs")
    if not isinstance(jobs, list):
        raise ValueError("Expected 'jobs' to be a list in the network schema.")

    cleaned_jobs = [
        job
        for job in jobs
        if isinstance(job, dict) and job.get("job_id") not in EXCLUDED_JOB_IDS
    ]

    if len(cleaned_jobs) == len(jobs):
        return user_schema

    cleaned_schema = user_schema.copy()
    cleaned_schema["jobs"] = cleaned_jobs

    return cleaned_schema
