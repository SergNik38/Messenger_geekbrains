import logging
import os

PATH = os.path.split(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(PATH[0], 'logs/client.log')

CLIENT_FORMATTER = logging.Formatter('%(levelname)s | %(asctime)s | %(filename)s | %(message)s')

FILE_HANDLER = logging.FileHandler(PATH)
FILE_HANDLER.setFormatter(CLIENT_FORMATTER)

LOG = logging.getLogger('client_logger')
LOG.setLevel(logging.DEBUG)
LOG.addHandler(FILE_HANDLER)

if __name__ == '__main__':
    LOG.debug('test debug message')
    LOG.info('test info message')
    LOG.error('test error message')
    LOG.critical('test critical message')