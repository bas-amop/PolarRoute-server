from pathlib import Path

from .base import *

MESH_PATH = Path("tests", "fixtures", "test_vessel_mesh.json")
MESH_DIR = Path("tests", "fixtures")

CELERY_BROKER_URL = "memory://"
CELERY_RESULT_BACKEND = "db+sqlite:///results.sqlite"
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_STORE_EAGER_RESULT = True
CELERY_TASK_EAGER_PROPAGATES = True
