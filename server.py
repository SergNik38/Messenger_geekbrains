import socket
import time
import project_logs.config.server_logs_config
import logging
from common.const import *
from common.utils import get_message, send_message
from decors import Log
import select


class Server:
    SERVER_LOGGER = logging.getLogger('server_logger')

    def __init__(self, server_address=DEFAULT_IP_ADDRESS, server_port=DEFAULT_PORT):
        self.server_address = server_address
        self.server_port = int(server_port)

    @Log()
    def client_message_handler(self, message, messages_lst, client):
        self.SERVER_LOGGER.debug(f'Received message: {message}')

        if ACTION in message and message[ACTION] == PRESENCE \
                and TIME in message and USER in message and message[USER][ACCOUNT_NAME] == 'Guest':
            self.SERVER_LOGGER.info('Server response OK')
            send_message(client, {RESPONSE: 200})
        elif ACTION in message and message[ACTION] == MESSAGE and TIME in message and MESSAGE_TEXT in message:
            messages_lst.append((message[ACCOUNT_NAME], message[MESSAGE_TEXT]))
            return
        else:
            self.SERVER_LOGGER.error('Server response: 400')
            send_message(client, {
                RESPONSE: 400,
                ERROR: 'BAD REQUEST'
            })

    # @Log()
    def main(self):
        if self.server_port < 1024 or self.server_port > 65535:
            self.SERVER_LOGGER.critical('Invalid server port')
            raise ValueError
        self.SERVER_LOGGER.info(f'Server object created address: {self.server_address}, port: {self.server_port}')
        transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        transport.bind((self.server_address, self.server_port))
        transport.settimeout(0.2)
        transport.listen(MAX_CONNECTIONS)

        clients = []
        messages = []

        while True:
            try:
                client, client_addr = transport.accept()
            except OSError:
                pass
            else:
                self.SERVER_LOGGER.info(f'Client {client_addr} connected')
                clients.append(client)

            recv_data_lst = []
            send_data_lst = []
            err_lst = []

            try:
                if clients:
                    recv_data_lst, send_data_lst, err_lst = select.select(clients, clients, [], 0)
            except OSError:
                pass

            if recv_data_lst:
                for client_msg in recv_data_lst:
                    try:
                        self.client_message_handler(get_message(client_msg), messages, client_msg)
                    except:
                        self.SERVER_LOGGER.error(f'Client {client_msg.getpeername()} disconnected')
                        clients.remove(client_msg)

            if messages and send_data_lst:
                message = {
                    ACTION: MESSAGE,
                    SENDER: messages[0][0],
                    TIME: time.time(),
                    MESSAGE_TEXT: messages[0][1]
                }
                del messages[0]
                for waiting_client in send_data_lst:
                    try:
                        send_message(waiting_client, message)
                    except:
                        self.SERVER_LOGGER.error(f'Client {waiting_client.getpeername()} disconnected')
                        clients.remove(waiting_client)



if __name__ == '__main__':
    server = Server()
    server.main()
