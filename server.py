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
    def client_message_handler(self, message, messages_lst, client, clients, names):
        self.SERVER_LOGGER.debug(f'Received message: {message}')

        if ACTION in message and message[ACTION] == PRESENCE \
                and TIME in message and USER in message:
            if message[USER][ACCOUNT_NAME] not in names.keys():
                print(f'client message handler {message}')
                names[message[USER][ACCOUNT_NAME]] = client
                self.SERVER_LOGGER.info('Server response OK')
                send_message(client, {RESPONSE: 200})
            else:
                print('Account name already taken')
                self.SERVER_LOGGER.error('Server response: 400')
                send_message(client, {
                    RESPONSE: 400,
                    ERROR: 'BAD REQUEST'
                })
                clients.remove(client)
                client.close()
            return

        elif ACTION in message and message[ACTION] == MESSAGE and TIME in message \
                and MESSAGE_TEXT in message and DESTINATION in message and SENDER in message:
            messages_lst.append(message)
            return
        elif ACTION in message and message[ACTION] == EXIT and ACCOUNT_NAME in message:
            clients.remove(names[message[ACCOUNT_NAME]])
            names[message[ACCOUNT_NAME]].close()
            del names[message[ACCOUNT_NAME]]
            return
        else:
            self.SERVER_LOGGER.error('Server response: 400')
            send_message(client, {
                RESPONSE: 400,
                ERROR: 'BAD REQUEST'
            })
            return
    @Log()
    def message_handler(self, message, names, listen_socks):
        if message[DESTINATION] in names and names[message[DESTINATION]] in listen_socks:
            print(f'MESSAGE HANDLER \n {names[message[DESTINATION]]}')
            send_message(names[message[DESTINATION]], message)
            self.SERVER_LOGGER.info(f'Message to {message[DESTINATION]} '
                        f'from {message[SENDER]} sent.')
        elif message[DESTINATION] in names and names[message[DESTINATION]] not in listen_socks:
            raise ConnectionError
        else:
            self.SERVER_LOGGER.error(f'User {message[DESTINATION]} not registered')
    @Log()
    def main(self):
        if self.server_port < 1024 or self.server_port > 65535:
            self.SERVER_LOGGER.critical('Invalid server port')
            raise ValueError
        self.SERVER_LOGGER.info(f'Server object created address: {self.server_address}, port: {self.server_port}')
        transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        transport.bind((self.server_address, self.server_port))
        transport.settimeout(0.5)
        transport.listen(MAX_CONNECTIONS)

        clients = []
        messages = []

        names = {}

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
                        print(f'recv_data_lst {client_msg}')
                        self.client_message_handler(get_message(client_msg), messages, client_msg, clients, names)
                    except:
                        self.SERVER_LOGGER.error(f'Client {client_msg.getpeername()} disconnected')
                        clients.remove(client_msg)

            for msg in messages:
                try:
                    self.message_handler(msg, names, send_data_lst)
                except:
                    self.SERVER_LOGGER.info(f'Connection with {msg[DESTINATION]} lost.')
                    clients.remove(names[msg[DESTINATION]])
            messages.clear()
            # if messages and send_data_lst:
            #     message = {
            #         ACTION: MESSAGE,
            #         SENDER: messages[0][0],
            #         TIME: time.time(),
            #         MESSAGE_TEXT: messages[0][1]
            #     }
            #     del messages[0]
            #     for waiting_client in send_data_lst:
            #         try:
            #             send_message(waiting_client, message)
            #         except:
            #             self.SERVER_LOGGER.error(f'Client {waiting_client.getpeername()} disconnected')
            #             clients.remove(waiting_client)


if __name__ == '__main__':
    server = Server()
    server.main()
