import socket
import time
from common.const import ACTION, PRESENCE, TIME, USER, \
    ACCOUNT_NAME, RESPONSE, ERROR, DEFAULT_IP_ADDRESS, DEFAULT_PORT
from common.utils import get_message, send_message
import logging
import project_logs.config.client_logs_config


class Client:
    CLIENT_LOGGER = logging.getLogger('client_logger')

    def __init__(self, account_name='Guest', server_address=DEFAULT_IP_ADDRESS, server_port=DEFAULT_PORT):
        self.server_address = server_address
        self.server_port = int(server_port)
        self.account_name = account_name

    def create_presence(self):
        out_mes = {
            ACTION: PRESENCE,
            TIME: time.time(),
            USER: {
                ACCOUNT_NAME: self.account_name
            }
        }
        self.CLIENT_LOGGER.debug('Presence created')
        return out_mes

    def answer_handler(self, message):
        if RESPONSE in message:
            if message[RESPONSE] == 200:
                self.CLIENT_LOGGER.info('Server response OK')
                return 'OK'
            self.CLIENT_LOGGER.error(f'Server response {message[ERROR]}')
            return f'400 : {message[ERROR]}'
        self.CLIENT_LOGGER.critical('Invalid message')
        raise ValueError

    def main(self):
        if self.server_port < 1024 or self.server_port > 65535:
            self.CLIENT_LOGGER.critical('Invalid port')
            raise ValueError
        self.CLIENT_LOGGER.info(f'Client created, Account: {self.account_name}')
        transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        transport.connect((self.server_address, self.server_port))
        message = self.create_presence()
        send_message(transport, message)
        try:
            answer = self.answer_handler(get_message(transport))
            print(answer)
        except ValueError:
            self.CLIENT_LOGGER.error('Decoding error')
            print('Не удалось декодировать сообщение')


if __name__ == '__main__':
    client = Client()
    client.main()
