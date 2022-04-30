import threading
import logging
import select
import socket
import json
import hmac
import binascii
import os
from common.metaclasses import ServerMaker
from common.descriptors import Port
from common.const import *
from common.utils import send_message, get_message
from common.decors import login_required

new_connection = False
conflag_lock = threading.Lock()


class MessageProcessor(threading.Thread):
    SERVER_LOGGER = logging.getLogger('server_logger')
    port = Port()

    def __init__(self, database, server_address=DEFAULT_IP_ADDRESS, server_port=DEFAULT_PORT):
        self.server_address = server_address
        self.server_port = int(server_port)
        self.database = database
        self.clients = []
        self.messages = []
        self.names = dict()
        self.running = True
        super().__init__()

    def run(self):
        global new_connection
        self.SERVER_LOGGER.info(f'Server object created address: {self.server_address}, port: {self.server_port}')
        transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        transport.bind((self.server_address, self.server_port))
        transport.settimeout(0.5)
        transport.listen()

        while self.running:
            try:
                client, client_addr = transport.accept()
            except OSError:
                pass
            else:
                self.SERVER_LOGGER.info(f'Client {client_addr} connected')
                self.clients.append(client)

            recv_data_lst = []
            send_data_lst = []
            err_lst = []
            try:
                if self.clients:
                    recv_data_lst, send_data_lst, err_lst = select.select(self.clients, self.clients, [], 0)
            except OSError:
                pass

            if recv_data_lst:
                for client_msg in recv_data_lst:
                    try:
                        self.client_message_handler(get_message(client_msg), client_msg)
                    except:
                        self.SERVER_LOGGER.error(f'Client {client_msg.getpeername()} disconnected')
                        self.remove_client(client_msg)

            for msg in self.messages:
                try:
                    self.message_handler(msg, send_data_lst)
                except:
                    self.SERVER_LOGGER.info(f'Connection with {msg[DESTINATION]} lost.')
                    self.remove_client(self.names[msg[DESTINATION]])
                    self.database.user_logout(msg[DESTINATION])
                    del self.names[msg[DESTINATION]]
                    with conflag_lock:
                        new_connection = True

            self.messages.clear()

    def client_message_handler(self, message, client):
        global new_connection
        self.SERVER_LOGGER.debug(f'Received message: {message}')

        if ACTION in message and message[ACTION] == PRESENCE \
                and TIME in message and USER in message:
            print('CLIENT MSG RECV')
            self.authorize_user(message, client)

        elif ACTION in message and message[ACTION] == MESSAGE and TIME in message \
                and MESSAGE_TEXT in message and DESTINATION in message and SENDER in message:
            if message[DESTINATION] in self.names:
                self.messages.append(message)
                self.database.message_handler(message[SENDER], message[DESTINATION])
                send_message(client, RESPONSE_200)
            else:
                response = RESPONSE_400
                response[ERROR] = 'User not found'
                send_message(client, response)
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

        elif ACTION in message and message[ACTION] == EXIT and ACCOUNT_NAME in message \
                and self.names[message[ACCOUNT_NAME]] == client:
            self.database.user_logout(message[ACCOUNT_NAME])
            self.remove_client(self.names[message[ACCOUNT_NAME]])
            self.names[message[ACCOUNT_NAME]].close()
            del self.names[message[ACCOUNT_NAME]]
            with conflag_lock:
                new_connection = True
            return
        elif ACTION in message and message[ACTION] == PUBLIC_KEY_REQUEST and ACCOUNT_NAME in message:
            response = RESPONSE_511
            response[DATA] = self.database.get_pubkey(message[ACCOUNT_NAME])
            # может быть, что ключа ещё нет (пользователь никогда не логинился,
            # тогда шлём 400)
            if response[DATA]:
                try:
                    send_message(client, response)
                except OSError:
                    self.remove_client(client)
            else:
                response = RESPONSE_400
                response[ERROR] = 'Not key for current user'
                try:
                    send_message(client, response)
                except OSError:
                    self.remove_client(client)
        else:
            self.SERVER_LOGGER.error('Server response: 400')
            send_message(client, {
                RESPONSE: 400,
                ERROR: 'BAD REQUEST'
            })
            return

    def message_handler(self, message, listen_socks):
        if message[DESTINATION] in self.names and self.names[message[DESTINATION]] in listen_socks:
            print(f'MESSAGE HANDLER \n {self.names[message[DESTINATION]]}')
            send_message(self.names[message[DESTINATION]], message)
            self.SERVER_LOGGER.info(f'Message to {message[DESTINATION]} '
                                    f'from {message[SENDER]} sent.')
        elif message[DESTINATION] in self.names and self.names[message[DESTINATION]] not in listen_socks:
            raise ConnectionError
        else:
            self.SERVER_LOGGER.error(f'User {message[DESTINATION]} not registered')

    def authorize_user(self, message, sock):
        self.SERVER_LOGGER.debug(f'Starting auth process for user {message[USER]}')
        if message[USER][ACCOUNT_NAME] in self.names.keys():
            resp = RESPONSE_400
            resp[ERROR] = 'Username already exists'
            try:
                self.SERVER_LOGGER.debug(f'Username exists: {resp}')
                send_message(sock, resp)
            except OSError:
                self.SERVER_LOGGER.debug('OSError')
                pass
            self.remove_client(sock)
            sock.close()

        elif not self.database.check_user(message[USER][ACCOUNT_NAME]):
            resp = RESPONSE_400
            resp[ERROR] = 'User not registered'
            try:
                self.SERVER_LOGGER.debug(f'Unknown username, sending {resp}')
                send_message(sock, resp)
            except OSError:
                pass
            self.remove_client(sock)
            sock.close()
        else:
            self.SERVER_LOGGER.debug('Correct username, starting password check.')
            print('Correct username, psw check')
            msg_auth = RESPONSE_511
            random_str = binascii.hexlify(os.urandom(64))
            msg_auth[DATA] = random_str.decode('ascii')
            print('before hash')
            hash = hmac.new(self.database.get_hash(message[USER][ACCOUNT_NAME]), random_str, 'MD5')
            print(f'after hash {hash}')
            digest = hash.digest()
            self.SERVER_LOGGER.debug(f'Auth message = {msg_auth}')
            print('trying send msg')
            try:
                send_message(sock, msg_auth)
                print('psw chk send msg')
                ans = get_message(sock)
            except OSError as err:
                self.SERVER_LOGGER.debug('Error in auth, data:', exc_info=err)
                sock.close()
                return
            client_digest = binascii.a2b_base64(ans[DATA])
            if RESPONSE in ans and ans[RESPONSE] == 511 and hmac.compare_digest(
                    digest, client_digest):
                self.names[message[USER][ACCOUNT_NAME]] = sock
                client_ip, client_port = sock.getpeername()
                try:
                    send_message(sock, RESPONSE_200)
                except OSError:
                    self.remove_client(message[USER][ACCOUNT_NAME])
                self.database.user_login(
                    message[USER][ACCOUNT_NAME],
                    client_ip,
                    client_port,
                    message[USER][PUBLIC_KEY])
            else:
                resp = RESPONSE_400
                resp[ERROR] = 'Incorrect password'
                try:
                    send_message(sock, resp)
                except OSError:
                    pass
                self.remove_client(sock)
                sock.close()

    def remove_client(self, client):
        for name in self.names:
            if self.names[name] == client:
                self.database.user_logout(name)
                del self.names[name]
                break
        self.clients.remove(client)
        client.close()

    def service_update_lists(self):
        for client in self.names:
            try:
                send_message(self.names[client], RESPONSE_205)
            except OSError:
                self.remove_client(self.names[client])
