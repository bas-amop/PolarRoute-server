from pathlib import Path

from .base import *

TEST_MESH_PATH = Path("tests", "fixtures", "test_vessel_mesh.json")
TEST_ROUTE_PATH = Path("tests", "fixtures", "test_route.json")
MESH_DIR = Path("tests", "fixtures")
MESH_METADATA_DIR = MESH_DIR

CELERY_BROKER_URL = "memory://"
CELERY_RESULT_BACKEND = "db+sqlite:///results.sqlite"
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_STORE_EAGER_RESULT = True
CELERY_TASK_EAGER_PROPAGATES = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.path.join(BASE_DIR, "db.sqlite3"),
    }
}

# dictionary relating user-friendly name of data source with loader value used in vessel mesh json 
EXPECTED_MESH_DATA_SOURCES = {
    "bathymetry": "GEBCO",
    "current": "duacs_current",
    "sea ice concentration": "amsr",
    "thickness": "thickness",
    "density": "density",
}

# number of data files expected in data_sources.params.files related by loader name as above, no need to include any of length 1 or 0
EXPECTED_MESH_DATA_FILES = {
    "amsr": 3,
    "duacs_current": 3,
}