import binascii
import hashlib
import hmac
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

    new_message = pyqtSignal(dict)
    lost_connection = pyqtSignal()

    def __init__(
            self,
            account_name,
            password,
            keys,
            database,
            server_address=DEFAULT_IP_ADDRESS,
            server_port=DEFAULT_PORT):
        threading.Thread.__init__(self)
        QObject.__init__(self)

        self.database = database
        self.account_name = account_name
        self.transport = None
        print('OKK')
        self.pswd = password
        self.keys = keys
        self.connection_init(server_port, server_address)
        print('INIT DONE')
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
        self.CLIENT_LOGGER.info(
            f'Client created, Account: {self.account_name}')
        self.transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.transport.settimeout(5)
        connected = False
        for i in range(5):
            self.CLIENT_LOGGER.info(f'Connection to server {i + 1}')
            try:
                self.transport.connect((ip, port))
                print('trans con')
            except (OSError, ConnectionRefusedError):
                pass
            else:
                connected = True
                print('Connected true')
                break
            time.sleep(1)

        if not connected:
            self.CLIENT_LOGGER.critical('Connection error')
            raise ConnectionRefusedError('Connection error')
        print('CONNECTED')
        self.CLIENT_LOGGER.info('Connected')

        passwd_bytes = self.pswd.encode('utf-8')
        print(passwd_bytes)
        salt = self.account_name.lower().encode('utf-8')
        print('2')
        passwd_hash = hashlib.pbkdf2_hmac('sha512', passwd_bytes, salt, 10000)
        print('3')
        passwd_hash_string = binascii.hexlify(passwd_hash)
        print('4')

        pub_key = self.keys.publickey().export_key().decode('ascii')

        with sock_lock:
            presence = {
                ACTION: PRESENCE,
                TIME: time.time(),
                USER: {
                    ACCOUNT_NAME: self.account_name,
                    PUBLIC_KEY: pub_key
                }
            }
            try:
                send_message(self.transport, presence)
                answer = get_message(self.transport)
                if RESPONSE in answer:
                    if answer[RESPONSE] == 400:
                        raise OSError
                    elif answer[RESPONSE] == 511:
                        answer_data = answer[DATA]
                        hash = hmac.new(
                            passwd_hash_string, answer_data.encode('utf-8'), 'MD5')
                        digest = hash.digest()
                        my_answer = RESPONSE_511
                        my_answer[DATA] = binascii.b2a_base64(
                            digest).decode('ascii')
                        send_message(self.transport, my_answer)
                        self.answer_handler(get_message(self.transport))

            except (OSError, json.JSONDecodeError) as err:
                self.CLIENT_LOGGER.debug(f'Connection error.', exc_info=err)
                raise OSError('Connection error')

    def key_request(self, user):
        self.CLIENT_LOGGER.debug(f'Public key for {user}')
        req = {
            ACTION: PUBLIC_KEY_REQUEST,
            TIME: time.time(),
            ACCOUNT_NAME: user
        }
        with sock_lock:
            send_message(self.transport, req)
            ans = get_message(self.transport)
        if RESPONSE in ans and ans[RESPONSE] == 511:
            return ans[DATA]
        else:
            self.CLIENT_LOGGER.error(f'Key Error {user}.')

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
            self.CLIENT_LOGGER.debug(
                f'Received message from {message[SENDER]}:{message[MESSAGE_TEXT]}')

            self.new_message.emit(message)

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
                    self.CLIENT_LOGGER.debug(
                        f'Received message from server {message}')
                    self.answer_handler(message)
                finally:
                    self.transport.settimeout(5)
