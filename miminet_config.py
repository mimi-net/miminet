import os
import pathlib
from PIL import Image

from datetime import datetime

SECRET_KEY_FILE = os.path.join(pathlib.Path(__file__).parent, "miminet_secret.conf")
SECRET_KEY = ''

if os.path.exists(SECRET_KEY_FILE):
    with open(SECRET_KEY_FILE, 'r') as file:
        SECRET_KEY = file.read().rstrip()
else:
    print ("There is no SECRET_KEY_FILE, generate random SECRET_KEY")
    SECRET_KEY = os.urandom(16).hex()


SQLITE_DATABASE_NAME = 'miminet.db'

current_data = datetime.today().strftime('%Y-%m-%d')
SQLITE_DATABASE_BACKUP_NAME = 'backup_' + current_data + '.db'

def make_empty_network():
    default_network = '{"nodes" : [], "edges" : [], "jobs" : []}'
    return default_network

def check_image_with_pil(file):
    try:
        Image.open(file)
    except IOError:
        return False
    return True