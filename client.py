from common.const import *
import logging
import sys
from PyQt5.QtWidgets import QApplication
from client.client_db import ClientDatabase
from client.transport import ClientTransport
from client.main_window import ClientMainWindow
from client.start_dialog import UserNameDialog
import argparse
import os
from Crypto.PublicKey import RSA


CLIENT_LOGGER = logging.getLogger('client_logger')


def arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('addr', default=DEFAULT_IP_ADDRESS, nargs='?')
    parser.add_argument('port', default=DEFAULT_PORT, type=int, nargs='?')
    parser.add_argument('-n', '--name', default=None, nargs='?')
    parser.add_argument('-p', '--password', default='', nargs='?')
    namespace = parser.parse_args(sys.argv[1:])
    server_address = namespace.addr
    server_port = namespace.port
    client_name = namespace.name
    client_passwd = namespace.password
    return server_address, server_port, client_name, client_passwd


if __name__ == '__main__':
    server_address, server_port, client_name, client_passwd = arg_parser()
    client_app = QApplication(sys.argv)

    start_dialog = UserNameDialog()
    if not client_name or not client_passwd:
        client_app.exec_()
        if start_dialog.ok_pressed:
            client_name = start_dialog.client_name.text()
            client_passwd = start_dialog.client_passwd.text()

            del start_dialog
        else:
            exit(0)
    CLIENT_LOGGER.info(f'Started client server ip: {server_address}, '
                       f'server port: {server_port}, name: {client_name}')

    dir_path = os.path.dirname(os.path.realpath(__file__))
    key_file = os.path.join(dir_path, f'{client_name}.key')
    if not os.path.exists(key_file):
        keys = RSA.generate(2048, os.urandom)
        with open(key_file, 'wb') as key:
            key.write(keys.export_key())
    else:
        with open(key_file, 'rb') as key:
            keys = RSA.import_key(key.read())
    print('KEYS LOADED')
    database = ClientDatabase(client_name)

    try:
        transport = ClientTransport(
            client_name,
            client_passwd,
            keys,
            database,
            server_address=server_address,
            server_port=server_port)
        print('OK')
    except BaseException:
        exit(1)
    transport.daemon = True
    transport.start()

    main_window = ClientMainWindow(database, transport, keys)
    main_window.make_connection(transport)
    main_window.setWindowTitle(f'Messenger alpha release - {client_name}')
    client_app.exec_()

    transport.shutdown()
    transport.join()
