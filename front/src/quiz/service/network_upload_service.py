from typing import Dict, List, Tuple, Any
from celery_app import app
import json
import uuid


def create_check_task(network_json: str, requirements_json: str):
    """Prepare task network and send it to checking service."""

    network = json.loads(network_json)
    requirements = json.loads(requirements_json)

    prepared_data = prepare_task(network, requirements)
    prepared_data_json = [
        (json.dumps(net), json.dumps(req)) for net, req in prepared_data
    ]

    # send task
    app.send_task(
        "tasks.check_task_network",
        [prepared_data_json],
        routing_key="task-checking-routing-key",
        exchange="task-checking-exchange",
        exchange_type="direct",
    )


# Unnecessary for task checking: (ping, ping with options, TCP/UDP ping, TCP/UDP server)
EXCLUDED_JOB_IDS = (1, 2, 3, 4, 200, 201)


def prepare_task(user_network: dict, task_req: dict):
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

    # ... all task prepare logic should be here ...
    cleaned_network = clean_schema(user_network)
    network_scenarios = task_req["network_scenarios"]

    return get_configured_tasks(cleaned_network, network_scenarios)


def get_configured_tasks(schema: Dict[str, Any], scenarios: List[Dict]) -> List[Tuple]:
    """Divide single schema into several separated schemas according to requirements."""
    results: List[Tuple] = []

    for scenario in scenarios:
        modifications = scenario["modifications"]

        # Every scenario generates new schema and requirements,
        # we need it in additional checks
        scenario_schema = schema.copy()
        scenario_requirements = scenario["requirements"].copy()

        for modification in modifications:
            modification_keys = modification.keys()

            if len(modification.keys()) != 1:
                raise ValueError(
                    f"Incorrect requirements modification keys: {modification_keys}."
                )

            modification_name: str = modification_keys[0]
            modification_arg: Dict[str, str] = modification[modification_name]

            if modification_name == "remove_edge":
                edge_id: str = modification_arg["id"]

                # Break edge
                scenario_schema["edges"] = [
                    edge
                    for edge in scenario_schema["edges"]
                    if edge["data"]["id"] != edge_id
                ]
            elif modification_name == "add_ping":
                from_host_name: str = modification_arg["from"]
                to_host_name: str = modification_arg["to"]

                # Get first IP address in "to" host
                # (Not smart enough, but usually host has only 1 address)
                to_host_ip: str = [
                    node["interface"][0]["ip"]
                    for node in scenario_schema["nodes"]
                    if node["data"]["id"] == to_host_name
                ][0]

                # Add ping job
                scenario_schema["jobs"].append(
                    {
                        "id": uuid.uuid4().hex,
                        "job_id": 1,
                        "print_cmd": f"ping -c 1 {to_host_ip}",
                        "arg_1": f"{to_host_ip}",
                        "level": -1,
                        "host_id": from_host_name,
                    }
                )
            else:
                raise ValueError(
                    f"Unknown requirements modifier name: {modification_name}."
                )

        results.append((scenario_schema, scenario_requirements))

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
