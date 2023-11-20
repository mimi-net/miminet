import os

from dotenv import load_dotenv

load_dotenv()

broker_url = os.getenv("amqp_urls")

result_backend = os.getenv("backend_urls")

imports = ["tasks"]

redis_backend_health_check_interval = 30

redis_retry_on_timeout = True
