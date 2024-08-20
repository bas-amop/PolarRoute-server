import subprocess
import time

from django.conf import settings
import kombu.exceptions
import pytest

from polarrouteserver.celery import app

def _db_up() -> bool:
    """Use pg_isready command to check if db is up and accepting connections"""
    return subprocess.run(["pg_isready","-d",
                          settings.DATABASES['default']["NAME"],
                          "-h",settings.DATABASES['default']["HOST"],
                          "-p",str(settings.DATABASES['default']["PORT"]),
                          "-U",settings.DATABASES['default']["USER"]
                          ]).returncode == 0

@pytest.fixture(scope="session")
def database():

    # runs before test
    if not _db_up(): 
        subprocess.run(["make", "start-dev-db"])
        while not _db_up():
            # after starting db, wait and check if it's up before running test
            time.sleep(1)
    yield
    # runs after test
    subprocess.run(["make", "stop-dev-db"])
