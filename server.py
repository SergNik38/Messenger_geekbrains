import socket
import time
import project_logs.config.server_logs_config
import logging
from common.const import *
from common.utils import get_message, send_message
from decors import Log
import select
from descriptors import Port
from metaclasses import ServerMaker
from server_db import ServerStorage
import threading


class Server(threading.Thread, metaclass=ServerMaker):
    SERVER_LOGGER = logging.getLogger('server_logger')
    server_port = Port()

    def __init__(self, database, server_address=DEFAULT_IP_ADDRESS, server_port=DEFAULT_PORT):
        self.server_address = server_address
        self.server_port = int(server_port)
        self.database = database
        super().__init__()
        print('INIT DONE')

    @Log()
    def client_message_handler(self, message, messages_lst, client, clients, names):
        self.SERVER_LOGGER.debug(f'Received message: {message}')

        if ACTION in message and message[ACTION] == PRESENCE \
                and TIME in message and USER in message:
            if message[USER][ACCOUNT_NAME] not in names.keys():
                print(f'client message handler {message}')
                names[message[USER][ACCOUNT_NAME]] = client
                client_ip, client_port = client.getpeername()
                print(client_ip)
                print(client_port)
                self.database.user_login(message[USER][ACCOUNT_NAME], client_ip, client_port)
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
            self.database.user_logout(message[ACCOUNT_NAME])
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
    def run(self):
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




def print_help():
    print('Commands:')
    print('users - all users list')
    print('connected - all connected users list')
    print('loghist - user login history')
    print('help - all commands')
    print('exit - shutdown_server')


def main():
    database = ServerStorage()
    server = Server(database)
    server.daemon = True
    server.start()
    print_help()
    while True:
        command = input('Input command: ')
        if command == 'users':
            for user in sorted(database.list_users()):
                print(f'User: {user[0]}, last login: {user[1]}')
        elif command == 'help':
            print_help()
        elif command == 'connected':
            for user in sorted(database.list_active_users()):
                print(f'User: {user[0]}, connected {user[1]}:{user[2]}, connection time: {user[3]}')
        elif command == 'loghist':
            name = input('Input username to show history, or press Enter to show all users history')
            for user in sorted(database.login_history(name)):
                print(f'User {user[0]}, login time: {user[1]}, connected from {user[2]}:{user[3]}')
        elif command == 'exit':
            break
        else:
            print('unknown command')


if __name__ == '__main__':
    main()
