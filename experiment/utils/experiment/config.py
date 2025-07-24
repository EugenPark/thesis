import os
from dotenv import load_dotenv

load_dotenv()

PROJECT_ID = os.getenv("PROJECT_ID")
USER = os.getenv("USER")
NETWORK = "crdb-net"
TF_DIR = "infra"


def remote_dir(name: str):
    return f"/dev/disk/by-id/google-{name}-disk"
