import logging
import datetime
import sys

logging.basicConfig(filename='test.log', encoding='utf-8', level=logging.DEBUG)
logger = logging.getLogger(__name__)
 # dd/mm/YY H:M:S
logger.info('Starting ' + datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"))

def handle_exception(exc_type, exc_value, exc_traceback):
    logger.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

sys.excepthook = handle_exception

1/0
