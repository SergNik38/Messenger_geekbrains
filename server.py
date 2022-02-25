import socket
import time
from common.const import ACTION, PRESENCE, TIME, USER, \
    ACCOUNT_NAME, RESPONSE, ERROR, DEFAULT_IP_ADDRESS, DEFAULT_PORT, MAX_CONNECTIONS
from common.utils import get_message, send_message


class Server:

    def __init__(self, server_address=DEFAULT_IP_ADDRESS, server_port=DEFAULT_PORT):
        self.server_address = server_address
        self.server_port = int(server_port)

    def client_message_handler(self, message):
        if ACTION in message and message[ACTION] == PRESENCE \
                and TIME in message and USER in message and message[USER][ACCOUNT_NAME] == 'Guest':
            return {RESPONSE: 200}
        return {
            RESPONSE: 400,
            ERROR: 'BAD REQUEST'
        }

    def main(self):
        if self.server_port < 1024 or self.server_port > 65535:
            raise ValueError

        transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        transport.bind((self.server_address, self.server_port))

        transport.listen(MAX_CONNECTIONS)

        while True:
            client, client_addr = transport.accept()
            try:
                message = get_message(client)
                print(message)
                response = self.client_message_handler(message)
                send_message(client, response)
                client.close()
            except ValueError:
                print('Некорректное сообщение')
                client.close()


if __name__ == '__main__':
    server = Server('192.168.0.101', '8888')
    server.main()
