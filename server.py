import socket
import logging
from common.const import *
from common.utils import get_message, send_message
from common.decors import Log
import select
from common.descriptors import Port
from common.metaclasses import ServerMaker
from server.server_db import ServerStorage
import threading
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from server.core import MessageProcessor
from server.main_window import MainWindow
import configparser
import os
import sys

new_connection = False
conflag_lock = threading.Lock()


def main():
    config = configparser.ConfigParser()

    dir_path = os.path.dirname(os.path.realpath(__file__))
    config.read(f'{dir_path}/server.ini')
    listen_address, listen_port = config['SETTINGS']['default_address'], config['SETTINGS']['default_port']
    database = ServerStorage(
        os.path.join(config['SETTINGS']['database_path'],
                     config['SETTINGS']['database_file'])
    )

    server = MessageProcessor(
        database,
        server_address=listen_address,
        server_port=listen_port)
    server.daemon = True
    server.start()
    # print_help()

    server_app = QApplication(sys.argv)
    server_app.setAttribute(Qt.AA_DisableWindowContextHelpButton)
    main_window = MainWindow(database, server, config)
    server_app.exec_()
    server.running = False

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
