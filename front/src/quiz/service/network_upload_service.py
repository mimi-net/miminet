from typing import Dict, Any
from celery_app import app
import json


def create_check_task(network_json: str, requirements_json: str):
    """
    Prepare task and send it for processing.
    """

    network = json.loads(network_json)
    requirements = json.loads(requirements_json)

    prepared_data = prepare_network(network, requirements)
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


def prepare_network(user_network: dict, task_req: dict):
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

    return [(cleaned_network, task_req)]


# Unnecessary for task checking: (ping, ping with options, TCP/UDP ping, TCP/UDP server)
EXCLUDED_JOB_IDS = (1, 2, 3, 4, 200, 201)


def clean_schema(user_schema: Dict[str, Any]) -> Dict[str, Any]:
    """Remove unnecessary jobs (user pings, netcats) from the user's network schema."""
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
