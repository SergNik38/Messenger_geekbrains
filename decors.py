import sys
import logging
import project_logs.config.client_logs_config
import project_logs.config.server_logs_config
import traceback


if sys.argv[0].find('client') == -1:
    LOGGER = logging.getLogger('server_logger')
else:
    LOGGER = logging.getLogger('client_logger')


class Log:
    def __call__(self, func):
        def create_log(*args, **kwargs):
            res = func(*args, **kwargs)
            LOGGER.debug(
                f'Called function {func.__name__} with params {args, kwargs}. '
                f'From module {func.__module__}. '
                f'From function {traceback.format_stack()[0].strip().split()[-1]}. ', stacklevel=2
            )
            return res
        return create_log
