from pathlib import Path
import yaml

from .base import *

# DEBUG = False

with open(Path("config", "staging.yaml"), "r") as f:
    config = yaml.load(f, Loader=yaml.Loader)

MESH_PATH = config.get("mesh_path")

ALLOWED_HOSTS.extend(config.get("allowed_hosts"))

CELERY_BROKER_URL=config.get("celery_broker_url")
