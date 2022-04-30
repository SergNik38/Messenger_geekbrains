import logging

LOGGER = logging.getLogger('server_logger')


class Port:
    def __set__(self, instance, value):
        if value < 1024 or value > 65535:
            LOGGER.critical('Invalid server port')
            print('Invalid server port')
            raise ValueError
        instance.__dict__[self.name] = value

    def __set_name__(self, owner, name):
        self.name = name
