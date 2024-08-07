import yaml
from pathlib import Path

from .base import *

with open(Path("config", "development.yaml"), "r") as f:
    config = yaml.load(f, Loader=yaml.Loader)

MESH_PATH = config.get("mesh_path")
