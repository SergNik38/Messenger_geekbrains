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
from client_db import ClientDatabase
import argparse


class Client(threading.Thread, metaclass=ClientMaker):
    CLIENT_LOGGER = logging.getLogger('client_logger')
    sock_lock = threading.Lock()
    db_lock = threading.Lock()

    def __init__(self, account_name, database, server_address=DEFAULT_IP_ADDRESS,
                 server_port=DEFAULT_PORT):
        self.database = database
        self.server_address = server_address
        self.server_port = int(server_port)
        self.account_name = account_name
        super().__init__()

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
        print('Type "edit" to edit contacts')
        print('Type "contacts" to show contacts list')
        print('Type "history" to show messages history')

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
        with self.db_lock:
            self.database.save_message(self.account_name, dest, message)

        with self.sock_lock:
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
            elif command == 'contacts':
                with self.db_lock:
                    contacts = self.database.get_contacts()
                for contact in contacts:
                    print(contact)
            elif command == 'edit':
                self.edit_contacts(sock)
            elif command == 'history':
                self.messages_history()

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

    def add_contact(self, sock, name, contact):
        self.CLIENT_LOGGER.debug('Making new contact')
        msg = {
            ACTION: ADD_CONTACT,
            TIME: time.time(),
            USER: name,
            ACCOUNT_NAME: contact
        }
        send_message(sock, msg)
        answer = get_message(sock)
        if RESPONSE in answer and answer[RESPONSE] == 200:
            print('Created new contact')
        else:
            raise Exception('Making contact error')

    def edit_contacts(self, sock):
        command = input('To delete contact type "del", to add contact type "add": ')
        if command == 'del':
            contact = input('Input name of contact to delete: ')
            with self.db_lock:
                if self.database.check_contact(contact):
                    self.database.delete_contact(contact)
                else:
                    self.CLIENT_LOGGER.error('Contact not found')
        if command == 'add':
            contact = input('Input name of contact to add')
            if self.database.check_user(contact):
                with self.db_lock:
                    self.database.add_contact(contact)
                with self.sock_lock:
                    try:
                        self.add_contact(sock, self.account_name, contact)
                    except:
                        self.CLIENT_LOGGER.error('Server connection error (edit_contact)')

    def messages_history(self):
        command = input('To show incoming messages type "in", to show sent messages type "out",'
                        'press Enter to show all')
        with self.db_lock:
            if command == 'in':
                hist_list = self.database.get_history(to_user=self.account_name)
                for msg in hist_list:
                    print(f'\nMessage from user {msg[0]} from {msg[3]}:{msg[2]}')
            elif command == 'out':
                hist_list = self.database.get_history(from_user=self.account_name)
                for msg in hist_list:
                    print(f'\nMessage to user {msg[1]} from {msg[3]}:{msg[2]}')
            else:
                hist_list = self.database.get_history()
                for msg in hist_list:
                    print(f'\nMessage from user {msg[0]} to {msg[1]} from {msg[3]}:{msg[2]}')

    def users_list(self, sock, username):
        msg = {
            ACTION: USERS_REQUEST,
            TIME: time.time(),
            ACCOUNT_NAME: username
        }
        send_message(sock, msg)
        answer = get_message(sock)
        if RESPONSE in answer and answer[RESPONSE] == 202:
            return answer[LIST_INFO]
        else:
            raise Exception('Response Error (users_list)')

    def contacts_list(self, sock, name):
        msg = {
            ACTION: GET_CONTACTS,
            TIME: time.time(),
            USER: name
        }
        send_message(sock, msg)
        answer = get_message(sock)
        if RESPONSE in answer and answer[RESPONSE] == 202:
            return answer[LIST_INFO]
        else:
            raise Exception('Response error (contacts_list)')

    def db_load(self, sock, name):
        try:
            users_list = self.users_list(sock, name)
        except:
            self.CLIENT_LOGGER.error('db_load error (users)')
        else:
            self.database.add_users(users_list)

        try:
            contacts_list = self.contacts_list(sock, name)
        except:
            self.CLIENT_LOGGER.error('db_load error (contacts)')
        else:
            for contact in contacts_list:
                self.database.add_contact(contact)

    @Log()
    def run(self):
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
            self.db_load(transport, self.account_name)
            print('Connected')
        except:
            self.CLIENT_LOGGER.error(f'Connection error (main)')
            sys.exit(1)
        else:
            # self.interface(transport)
            user_interface = threading.Thread(target=self.interface, args=(transport,))
            user_interface.daemon = True
            user_interface.start()

            # self.receive_message(transport, self.account_name)
            receiving = threading.Thread(target=self.receive_message, args=(transport, self.account_name))
            receiving.daemon = True
            receiving.start()
            self.CLIENT_LOGGER.debug('Process started')

            while True:
                time.sleep(1)
                if receiving.is_alive() and user_interface.is_alive():
                    continue
                break



def main():
    client_name = input('Input your name: ')
    db = ClientDatabase(client_name)
    client = Client(account_name=client_name, database=db)
    client.daemon = True
    client.run()


if __name__ == '__main__':
    main()
