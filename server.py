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
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import QTimer
from server_gui import MainWindow, gui_create_model, HistoryWindow, create_stat_model, ConfigWindow
from PyQt5.QtGui import QStandardItemModel, QStandardItem
import configparser
import os
import sys

new_connection = False
conflag_lock = threading.Lock()


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
        global new_connection
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
                with conflag_lock:
                    new_connection = True
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
            self.database.message_handler(message[SENDER], message[DESTINATION])
            return
        elif ACTION in message and message[ACTION] == GET_CONTACTS and USER in message:
            response = RESPONSE_202
            response[LIST_INFO] = self.database.get_contacts(message[USER])
            send_message(client, response)

        elif ACTION in message and message[ACTION] == ADD_CONTACT and ACCOUNT_NAME in message \
                and USER in message:

            self.database.add_contact(message[USER], message[ACCOUNT_NAME])
            send_message(client, RESPONSE_200)

        elif ACTION in message and message[ACTION] == REMOVE_CONTACT and ACCOUNT_NAME in message \
                and USER in message:
            self.database.del_contact(message[USER], message[ACCOUNT_NAME])
            send_message(client, {RESPONSE: 200})

        elif ACTION in message and message[ACTION] == USERS_REQUEST and ACCOUNT_NAME in message:
            response = RESPONSE_202
            response[LIST_INFO] = [user[0] for user in self.database.list_users()]
            send_message(client, response)

        elif ACTION in message and message[ACTION] == EXIT and ACCOUNT_NAME in message:
            self.database.user_logout(message[ACCOUNT_NAME])
            clients.remove(names[message[ACCOUNT_NAME]])
            names[message[ACCOUNT_NAME]].close()
            del names[message[ACCOUNT_NAME]]
            with conflag_lock:
                new_connection = True
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
        transport.listen()
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
                    self.database.user_logout(msg[DESTINATION])
                    del names[messages[DESTINATION]]

            messages.clear()


def print_help():
    print('Commands:')
    print('users - all users list')
    print('connected - all connected users list')
    print('loghist - user login history')
    print('help - all commands')
    print('exit - shutdown_server')

def main():
    config = configparser.ConfigParser()

    dir_path = os.path.dirname(os.path.realpath(__file__))
    config.read(f'{dir_path}/server.ini')
    listen_address, listen_port = config['SETTINGS']['default_address'], config['SETTINGS']['default_port']
    database = ServerStorage(
        os.path.join(config['SETTINGS']['database_path'],
                     config['SETTINGS']['database_file'])
    )

    server = Server(database, server_address=listen_address, server_port=listen_port)
    server.daemon = True
    server.start()
    # print_help()

    server_app = QApplication(sys.argv)
    main_window = MainWindow()

    main_window.statusBar().showMessage('Server working')
    main_window.active_clients.setModel(gui_create_model(database))
    main_window.active_clients.resizeColumnsToContents()
    main_window.active_clients.resizeRowsToContents()

    def list_update():
        global new_connection
        if new_connection:
            main_window.active_clients.setModel(
                gui_create_model(database))
            main_window.active_clients.resizeColumnsToContents()
            main_window.active_clients.resizeRowsToContents()
        with conflag_lock:
            new_connection = False

    def show_stats():
        global stat_window
        stat_window = HistoryWindow()
        stat_window.history.setModel(create_stat_model(database))
        stat_window.history.resizeColumnsToContents()
        stat_window.history.resizeRowsToContents()
        stat_window.show()

    def save_server_config():
        global config_window
        message = QMessageBox()
        config['SETTINGS']['database_path'] = config_window.db_path.text()
        config['SETTINGS']['database_file'] = config_window.db_file.text()
        try:
            port = int(config_window.port.text())
        except ValueError:
            message.warning(config_window, 'Error', 'Port must be Integer')
        else:
            config['SETTINGS']['default_address'] = config_window.ip.text()
            if 1023 < port < 65536:
                config['SETTINGS']['default_port'] = str(port)
                print(port)
                with open('server.ini', 'w') as conf:
                    config.write(conf)
                    message.information(
                        config_window, 'OK', 'Settings save successful')
            else:
                message.warning(
                    config_window, 'Error', 'Incorrect Port')

    def server_config():
        global config_window
        # Создаём окно и заносим в него текущие параметры
        config_window = ConfigWindow()
        config_window.db_path.insert(config['SETTINGS']['database_path'])
        config_window.db_file.insert(config['SETTINGS']['database_file'])
        config_window.port.insert(config['SETTINGS']['default_port'])
        config_window.ip.insert(config['SETTINGS']['default_address'])
        config_window.save_btn.clicked.connect(save_server_config)

    timer = QTimer()
    timer.timeout.connect(list_update)
    timer.start(1000)

    main_window.refresh_btn.triggered.connect(list_update)
    main_window.show_history_btn.triggered.connect(show_stats)
    main_window.config_btn.triggered.connect(server_config)

    server_app.exec_()


    # while True:
    #     command = input('Input command: ')
    #     if command == 'users':
    #         for user in sorted(database.list_users()):
    #             print(f'User: {user[0]}, last login: {user[1]}')
    #     elif command == 'help':
    #         print_help()
    #     elif command == 'connected':
    #         for user in sorted(database.list_active_users()):
    #             print(f'User: {user[0]}, connected {user[1]}:{user[2]}, connection time: {user[3]}')
    #     elif command == 'loghist':
    #         name = input('Input username to show history, or press Enter to show all users history')
    #         for user in sorted(database.login_history(name)):
    #             print(f'User {user[0]}, login time: {user[1]}, connected from {user[2]}:{user[3]}')
    #     elif command == 'exit':
    #         break
    #     else:
    #         print('unknown command')


if __name__ == '__main__':
    main()
