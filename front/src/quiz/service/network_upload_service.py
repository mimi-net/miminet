from miminet_model import Network
from sqlalchemy import func
from celery_app import (
    app,
)


def upload_task_network():
    """
    Prepare task and send it.
    """
    # You need to pass into 'prepare_task_network' user's network schema and task requirements
    # I just use test data for example
    net = Network.query.order_by(func.random()).first()
    schema = net.network
    req = "*here should be requirements*"

    res_data = prepare_task_network(schema, req)

    # send task
    app.send_task(
        "tasks.check_task_network",
        [res_data],
        routing_key="task-checking-routing-key",
        exchange="task-checking-exchange",
        exchange_type="direct",
    )

    # return "OK" code
    return 200


def prepare_task_network(user_network: Network, task_req: str):
    """
    Prepare task according to requirements:
    - Split task to several separate network schemas,
    - Modify these schemas.

    Args:
        user_network (Network): Network schema developed by user.
        task_req (str): Task requirements (description of what we need to check).

    Returns:
        List[Tuple]: List of tuples (network schema, requirements).
    """

    # ... all task prepare logic should be here ...

    return [(user_network, task_req)]
