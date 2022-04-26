import socket
import sys
import time
import logging
import json
import threading
from PyQt5.QtCore import pyqtSignal, QObject

from common.utils import *
from common.const import *

sock_lock = threading.Lock()

class ClientTransport(threading.Thread, QObject):
    CLIENT_LOGGER = logging.getLogger('client_logger')
    sock_lock = threading.Lock()

    new_message = pyqtSignal(str)
    lost_connection = pyqtSignal()

    def __init__(self, account_name, database, server_address=DEFAULT_IP_ADDRESS,
                 server_port=DEFAULT_PORT):
        threading.Thread.__init__(self)
        QObject.__init__(self)

        self.database = database
        self.account_name = account_name
        self.transport = None
        self.connection_init(server_port, server_address)

        try:
            self.users_list_update()
            self.contacts_list_update()
        except OSError as err:
            if err.errno:
                self.CLIENT_LOGGER.critical('Lost connection to server')
                raise OSError('Lost connection')
            self.CLIENT_LOGGER.error('Connection timeout')
        except json.JSONDecodeError:
            self.CLIENT_LOGGER.critical('Lost connection to server')
            raise OSError('Lost connection')
        self.running = True

    def connection_init(self, port, ip):
        if port < 1024 or port > 65535:
            self.CLIENT_LOGGER.critical('Invalid port')
            raise ValueError
        self.CLIENT_LOGGER.info(f'Client created, Account: {self.account_name}')
        self.transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.transport.settimeout(5)
        connected = False
        for i in range(5):
            self.CLIENT_LOGGER.info(f'Connection to server {i+1}')
            try:
                self.transport.connect((ip, port))
            except (OSError, ConnectionRefusedError):
                pass
            else:
                connected = True
                break
            time.sleep(1)
        if not connected:
            self.CLIENT_LOGGER.critical('Connection error')
            raise ConnectionRefusedError('Connection error')
        self.CLIENT_LOGGER.info('Connected')

        try:
            with sock_lock:
                send_message(self.transport, self.create_presence())
                self.answer_handler(get_message(self.transport))
        except (OSError, json.JSONDecodeError):
            self.CLIENT_LOGGER.critical('Connection lost')
            raise OSError('Connection lost')
        self.CLIENT_LOGGER.info('Connected successful')

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

    def answer_handler(self, message):
        if RESPONSE in message:
            if message[RESPONSE] == 200:
                print('RESPONSE OK')
                self.CLIENT_LOGGER.info('Server response OK')
                return
            elif message[RESPONSE] == 400:
                raise ValueError('Answer error')
        elif ACTION in message and message[ACTION] == MESSAGE and SENDER in message and DESTINATION in message \
                and MESSAGE_TEXT in message and message[DESTINATION] == self.account_name:
            self.CLIENT_LOGGER.debug(f'Received message from {message[SENDER]}:{message[MESSAGE_TEXT]}')
            self.database.save_message(message[SENDER], 'in', message[MESSAGE_TEXT])
            print('MESSAGE RECEIVED')
            self.new_message.emit(message[SENDER])

    def contacts_list_update(self):
        msg = {
            ACTION: GET_CONTACTS,
            TIME: time.time(),
            USER: self.account_name
        }
        with sock_lock:
            send_message(self.transport, msg)
            answer = get_message(self.transport)
        self.CLIENT_LOGGER.debug(f'Anser received {answer}')
        if RESPONSE in answer and answer[RESPONSE] == 202:
            for contact in answer[LIST_INFO]:
                self.database.add_contact(contact)
        else:
            self.CLIENT_LOGGER.error('Response error (contacts_list)')

    def users_list_update(self):
        msg = {
            ACTION: USERS_REQUEST,
            TIME: time.time(),
            ACCOUNT_NAME: self.account_name
        }
        with sock_lock:
            send_message(self.transport, msg)
            answer = get_message(self.transport)
        if RESPONSE in answer and answer[RESPONSE] == 202:
            self.database.add_users(answer[LIST_INFO])
        else:
            self.CLIENT_LOGGER.error('Response Error (users_list)')

    def add_contact(self, contact):
        self.CLIENT_LOGGER.debug('Making new contact')
        msg = {
            ACTION: ADD_CONTACT,
            TIME: time.time(),
            USER: self.account_name,
            ACCOUNT_NAME: contact
        }
        with sock_lock:
            send_message(self.transport, msg)
            self.answer_handler(get_message(self.transport))

    def remove_contact(self, contact):
        self.CLIENT_LOGGER.debug(f'Removing contact {contact}')
        msg = {
            ACTION: REMOVE_CONTACT,
            TIME: time.time(),
            USER: self.account_name,
            ACCOUNT_NAME: contact
        }
        with sock_lock:
            send_message(self.transport, msg)
            self.answer_handler(get_message(self.transport))

    def shutdown(self):
        self.running = False
        msg = {
            ACTION: EXIT,
            TIME: time.time(),
            ACCOUNT_NAME: self.account_name
        }
        with sock_lock:
            try:
                send_message(self.transport, msg)
            except OSError:
                pass
        self.CLIENT_LOGGER.debug('Transport shutdown')
        time.sleep(0.5)

    def send_message(self, dest, message):
        msg = {
            ACTION: MESSAGE,
            SENDER: self.account_name,
            DESTINATION: dest,
            TIME: time.time(),
            MESSAGE_TEXT: message
        }
        with sock_lock:
            send_message(self.transport, msg)
            self.answer_handler(get_message(self.transport))
            print('MESSAGE SENT')
            self.CLIENT_LOGGER.debug('Message created')

    def run(self):
        self.CLIENT_LOGGER.debug('Receiving messages started')

        while self.running:
            time.sleep(1)
            with sock_lock:
                try:
                    self.transport.settimeout(0.5)
                    message = get_message(self.transport)
                except OSError as err:
                    if err.errno:
                        self.CLIENT_LOGGER.critical('Connection lost')
                        self.running = False
                        self.lost_connection.emit()

                except (ConnectionError, ConnectionAbortedError,
                        ConnectionResetError, json.JSONDecodeError, TypeError):
                    self.CLIENT_LOGGER.critical('Connection lost')
                    self.running = False
                    self.lost_connection.emit()
                else:
                    self.CLIENT_LOGGER.debug(f'Received message from server {message}')
                    self.answer_handler(message)
                finally:
                    self.transport.settimeout(5)




