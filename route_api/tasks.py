import time
import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def calculate_route(msg):
    # dummy long-running process for initial development
    time.sleep(15)

    # locate relevant mesh file
    # route calculation/optimisation using polar route
    # put route metadata in database
    # what to return? serialized Route object?

    return msg
