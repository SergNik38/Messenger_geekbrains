import json
import socket
import time
from common.const import *
from common.utils import get_message, send_message
import logging
import project_logs.config.client_logs_config
from decors import Log
import sys
import threading
from metaclasses import ClientMaker


class Client(metaclass=ClientMaker):
    CLIENT_LOGGER = logging.getLogger('client_logger')

    def __init__(self, account_name, server_address=DEFAULT_IP_ADDRESS,
                 server_port=DEFAULT_PORT):
        self.server_address = server_address
        self.server_port = int(server_port)
        self.account_name = account_name

    @Log()
    def create_presence(self):
        out_mes = {
            ACTION: PRESENCE,
            TIME: time.time(),
            USER: {
                ACCOUNT_NAME: self.account_name
            }
        }
        self.CLIENT_LOGGER.debug(f'Presence created {self.account_name}')
        return out_mes

    @Log()
    def receive_message(self, sock, account):
        while True:
            try:
                message = get_message(sock)
                if ACTION in message and message[ACTION] == MESSAGE and SENDER in message \
                        and MESSAGE_TEXT in message and DESTINATION in message and message[DESTINATION] == account:
                    print(f'Message from {message[SENDER]}: {message[MESSAGE_TEXT]}')
                    self.CLIENT_LOGGER.info(f'Message from {message[SENDER]}: {message[MESSAGE_TEXT]}')
                    continue
                else:
                    self.CLIENT_LOGGER.error(f'Invalid message from server: {message}')
            except:
                print(f'Connection lost')
                break

    def help_screen(self):
        print('Commands:')
        print('Input exit to close connection;')
        print('Input message to send message;')

    def create_message(self, sock):
        dest = input(f'Input message destination: ')
        message = input(f'Input message: ')
        message_dict = {
            ACTION: MESSAGE,
            SENDER: self.account_name,
            DESTINATION: dest,
            TIME: time.time(),
            MESSAGE_TEXT: message
        }
        self.CLIENT_LOGGER.info(f'Message dict created: {message_dict}')
        try:
            send_message(sock, message_dict)
            self.CLIENT_LOGGER.info(f'Sending message to {dest}')
        except:
            self.CLIENT_LOGGER.critical('Connection error (create_message)')
            sys.exit(1)

    @Log()
    def interface(self, sock):
        self.help_screen()

        while True:
            command = input('Command: ')
            if command == 'message':
                self.create_message(sock)
            elif command == 'help':
                self.help_screen()
            elif command == 'exit':
                exit_dict = {
                    ACTION: EXIT,
                    TIME: time.time(),
                    ACCOUNT_NAME: self.account_name}
                send_message(sock, exit_dict)
                print('Closing connection')
                self.CLIENT_LOGGER.info(f'Closing connection {self.account_name}')
                time.sleep(0.5)
                break
            else:
                print('Unknown command')

    @Log()
    def answer_handler(self, message):
        if RESPONSE in message:
            if message[RESPONSE] == 200:
                self.CLIENT_LOGGER.info('Server response OK')
                return 'OK'
            self.CLIENT_LOGGER.error(f'Server response {message[ERROR]}')
            return f'400 : {message[ERROR]}'
        self.CLIENT_LOGGER.critical('Invalid message')
        raise ValueError

    @Log()
    def main(self):
        if self.server_port < 1024 or self.server_port > 65535:
            self.CLIENT_LOGGER.critical('Invalid port')
            raise ValueError
        self.CLIENT_LOGGER.info(f'Client created, Account: {self.account_name}')
        try:
            transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            transport.connect((self.server_address, self.server_port))
            send_message(transport, self.create_presence())
            answer = self.answer_handler(get_message(transport))
            self.CLIENT_LOGGER.info(f'Connected. Server answer: {answer}')
            print('Connected')
        except:
            self.CLIENT_LOGGER.error(f'Connection error (main)')
            sys.exit(1)
        else:
            user_interface = threading.Thread(target=self.interface, args=(transport,))
            user_interface.daemon = True
            user_interface.start()

            receiving = threading.Thread(target=self.receive_message, args=(transport, self.account_name))
            receiving.daemon = True
            receiving.start()
            self.CLIENT_LOGGER.debug('Process started')

            while True:
                time.sleep(1)
                if receiving.is_alive() and user_interface.is_alive():
                    continue
                break


if __name__ == '__main__':
    client = Client(account_name=input('Input name: '))
    client.main()
