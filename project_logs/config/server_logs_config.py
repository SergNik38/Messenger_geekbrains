import logging
import logging.handlers
import os

PATH = os.path.split(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(PATH[0], 'logs/server.log')

SERVER_FORMATTER = logging.Formatter('%(levelname)s | %(asctime)s | %(filename)s | %(message)s')
FILE_HANDLER = logging.handlers.TimedRotatingFileHandler(PATH, encoding='utf-8', interval=1, when='midnight')
FILE_HANDLER.setFormatter(SERVER_FORMATTER)

LOG = logging.getLogger('server_logger')
LOG.setLevel(logging.DEBUG)
LOG.addHandler(FILE_HANDLER)

if __name__ == '__main__':
    LOG.debug('test debug message')
    LOG.info('test info message')
    LOG.error('test error message')
    LOG.critical('test critical message')
