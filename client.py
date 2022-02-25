import socket
import time
from common.const import ACTION, PRESENCE, TIME, USER, \
    ACCOUNT_NAME, RESPONSE, ERROR, DEFAULT_IP_ADDRESS, DEFAULT_PORT
from common.utils import get_message, send_message


class Client:

    def __init__(self, account_name, server_address=DEFAULT_IP_ADDRESS, server_port=DEFAULT_PORT):
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
        return out_mes

    def answer_handler(self, message):
        if RESPONSE in message:
            if message[RESPONSE] == 200:
                return 'OK'
            return 'ERROR'
        raise ValueError

    def main(self):
        if self.server_port < 1024 or self.server_port > 65535:
            raise ValueError

        transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        transport.connect((self.server_address, self.server_port))
        message = self.create_presence()
        send_message(transport, message)
        try:
            answer = self.answer_handler(get_message(transport))
            print(answer)
        except ValueError:
            print('Не удалось декодировать сообщение')


if __name__ == '__main__':
    client = Client('Guest', '192.168.0.101', '8888')
    client.main()
