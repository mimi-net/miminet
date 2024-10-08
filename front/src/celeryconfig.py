import os

from dotenv import load_dotenv

load_dotenv()

broker_url = os.getenv("amqp_urls")

imports = ["tasks"]
