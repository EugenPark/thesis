import os
from dotenv import load_dotenv

load_dotenv()

PROJECT_ID = os.getenv("PROJECT_ID")
REMOTE_DIR = os.getenv("REMOTE_DIR")
NETWORK = "crdb-net"
TF_DIR = "infra"
