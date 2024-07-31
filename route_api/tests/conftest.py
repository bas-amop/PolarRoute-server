import pytest


@pytest.fixture(scope="session")
def celery_config():
    return {
        "broker_url": "amqp://guest:guest@localhost",
        # 'result_backend': 'redis://'
    }
