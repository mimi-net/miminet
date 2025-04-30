import os

from dotenv import load_dotenv

load_dotenv()

broker_url = os.getenv("amqp_urls")
result_backend = os.getenv("rpc_urls")

imports = ["tasks"]

broker_connection_retry_on_startup = True
