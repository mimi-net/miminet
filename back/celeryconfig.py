import os

from random import shuffle
from dotenv import load_dotenv

load_dotenv()

broker_url = os.getenv('amqp_urls')

result_backend = os.getenv('backend_urls')

imports = ['tasks']

redis_backend_health_check_interval = 30

redis_retry_on_timeout = True


# random broker strategy
def get_amqp(urls):
    urls_list = list(urls)
    while True:
        shuffle(urls_list)
        yield urls_list[0]


broker_failover_strategy = get_amqp
