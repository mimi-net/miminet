from miminet_model import Network
from sqlalchemy import func

# from celery_app import (
#     SEND_NETWORK_EXCHANGE,
#     EXCHANGE_TYPE,
#     app,
# )


def upload_task_network():
    """
    Prepare task and send it.
    """
    # You need to pass into 'prepare_task_network' user's network schema and task requirements
    # I just use test data for example
    net = Network.query.order_by(func.random()).first()
    req = "*here should be requirements*"

    prepare_task_network(net, req)

    # send task
    # app.send_task(
    #         "tasks.mininet_worker",
    #         (net.network,),
    #         routing_key=str(uuid.uuid4()),
    #         exchange=SEND_NETWORK_EXCHANGE,
    #         exchange_type=EXCHANGE_TYPE,
    #         task_id=str(task_guid),
    #         headers={"network_task_name": "tasks.save_simulate_result"},
    #     )

    # return status code
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
