import base64

from PyQt5.QtWidgets import QMainWindow, qApp, QMessageBox, QApplication, QListView
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QBrush, QColor
from PyQt5.QtCore import pyqtSlot, QEvent, Qt
import logging
from common.const import *
from client.main_window_conv import Ui_MainClientWindow
from client.add_contact import AddContactDialog
from client.delete_contact import DelContactDialog
from client.client_db import ClientDatabase
from client.transport import ClientTransport
from client.start_dialog import UserNameDialog
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP
import json
logger = logging.getLogger('client_logger')


class ClientMainWindow(QMainWindow):
    """Main window of client GUI"""
    def __init__(self, database, transport, keys):
        super().__init__()
        self.database = database
        self.transport = transport

        self.decrypter = PKCS1_OAEP.new(keys)
        self.ui = Ui_MainClientWindow()
        self.ui.setupUi(self)

        self.ui.menu_exit.triggered.connect(qApp.exit)

        self.ui.btn_send.clicked.connect(self.send_message)

        self.ui.btn_add_contact.clicked.connect(self.add_contact_window)
        self.ui.menu_add_contact.triggered.connect(self.add_contact_window)

        self.ui.btn_remove_contact.clicked.connect(self.delete_contact_window)
        self.ui.menu_del_contact.triggered.connect(self.delete_contact_window)

        self.contacts_model = None
        self.history_model = None
        self.messages = QMessageBox()
        self.current_chat = None
        self.current_chat_key = None
        self.encryptor = None
        self.ui.list_messages.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff)
        self.ui.list_messages.setWordWrap(True)

        self.ui.list_contacts.doubleClicked.connect(self.select_active_user)

        self.clients_list_update()
        self.set_disabled_input()
        self.show()

    def set_disabled_input(self):
        self.ui.label_new_message.setText('Choose contact')
        self.ui.text_message.clear()
        if self.history_model:
            self.history_model.clear()

        self.ui.btn_clear.setDisabled(True)
        self.ui.btn_send.setDisabled(True)
        self.ui.text_message.setDisabled(True)

        self.encryptor = None
        self.current_chat = None
        self.current_chat_key = None

    def history_list_update(self):
        lst = sorted(
            self.database.get_history(
                self.current_chat),
            key=lambda item: item[3])
        if not self.history_model:
            self.history_model = QStandardItemModel()
            self.ui.list_messages.setModel(self.history_model)
        self.history_model.clear()

        length = len(lst)
        start_idx = 0

        if length > 20:
            start_idx = length - 20

        for i in range(start_idx, length):
            item = lst[i]
            if item[1] == 'in':
                msg = QStandardItem(
                    f'Incoming message from {item[3].replace(microsecond=0)}:\n {item[2]}')
                msg.setEditable(False)
                msg.setBackground(QBrush(QColor(255, 213, 213)))
                msg.setTextAlignment(Qt.AlignLeft)
                self.history_model.appendRow(msg)
            else:
                msg = QStandardItem(
                    f'Outgoing message from {item[3].replace(microsecond=0)}:\n {item[2]}')
                msg.setEditable(False)
                msg.setTextAlignment(Qt.AlignRight)
                msg.setBackground(QBrush(QColor(204, 255, 204)))
                self.history_model.appendRow(msg)
        self.ui.list_messages.scrollToBottom()

    def select_active_user(self):
        self.current_chat = self.ui.list_contacts.currentIndex().data()
        self.set_active_user()

    def set_active_user(self):
        try:
            self.current_chat_key = self.transport.key_request(
                self.current_chat)
            logger.debug(f'Pubkey loaded {self.current_chat}')
            if self.current_chat_key:
                self.encryptor = PKCS1_OAEP.new(
                    RSA.import_key(self.current_chat_key))
        except (OSError, json.JSONDecodeError):
            self.current_chat_key = None
            self.encryptor = None
            logger.debug(f'Key not found {self.current_chat}')

        if not self.current_chat_key:
            self.messages.warning(
                self, 'Error', 'Not cryptokey')
            return

        self.ui.label_new_message.setText(
            f'Input message for {self.current_chat}:')
        self.ui.btn_clear.setDisabled(False)
        self.ui.btn_send.setDisabled(False)
        self.ui.text_message.setDisabled(False)

        self.history_list_update()

    def clients_list_update(self):
        contacts_list = self.database.get_contacts()
        self.contacts_model = QStandardItemModel()
        for i in sorted(contacts_list):
            item = QStandardItem(i)
            item.setEditable(False)
            self.contacts_model.appendRow(item)
        self.ui.list_contacts.setModel(self.contacts_model)

    def add_contact_window(self):
        global select_dialog
        select_dialog = AddContactDialog(self.transport, self.database)
        select_dialog.btn_ok.clicked.connect(
            lambda: self.add_contact_action(select_dialog))
        select_dialog.show()

    def add_contact_action(self, item):
        new_contact = item.selector.currentText()
        self.add_contact(new_contact)
        item.close()

    def add_contact(self, new_contact):
        try:
            self.transport.add_contact(new_contact)
        except OSError as err:
            if err.errno:
                self.messages.critical(self, 'Error', 'Lost connection')
                self.close()
            self.messages.critical(self, 'Error', 'Connection timeout')
        else:
            self.database.add_contact(new_contact)
            new_contact = QStandardItem(new_contact)
            new_contact.setEditable(False)
            self.contacts_model.appendRow(new_contact)
            logger.info(f'Contact added successfully {new_contact}')
            self.messages.information(self, 'Success', 'Contact added')

    def delete_contact_window(self):
        global remove_dialog
        remove_dialog = DelContactDialog(self.database)
        remove_dialog.btn_ok.clicked.connect(
            lambda: self.delete_contact(remove_dialog))
        remove_dialog.show()

    def delete_contact(self, item):
        selected = item.selector.currentText()
        try:
            self.transport.remove_contact(selected)
        except OSError as err:
            if err.errno:
                self.messages.critical(self, 'Error', 'Lost connection')
                self.close()
            self.messages.critical(self, 'Error', 'Connection timeout')
        else:
            self.database.delete_contact(selected)
            self.clients_list_update()
            logger.info(f'Successfully deleted {selected}')
            self.messages.information(self, 'Success', 'Contact deleted')
            item.close()
            if selected == self.current_chat:
                self.current_chat = None
                self.set_disabled_input()

    def send_message(self):
        message_text = self.ui.text_message.toPlainText()
        self.ui.text_message.clear()
        if not message_text:
            return
        message_text_encrypted = self.encryptor.encrypt(
            message_text.encode('utf8'))
        message_text_encrypted_base64 = base64.b64encode(
            message_text_encrypted)
        try:
            self.transport.send_message(
                self.current_chat,
                message_text_encrypted_base64.decode('ascii'))
            pass
        except OSError as err:
            if err.errno:
                self.messages.critical(self, 'Error', 'Lost connection!')
                self.close()
            self.messages.critical(self, 'Error', 'Connection timeout')
        except (ConnectionResetError, ConnectionAbortedError):
            self.messages.critical(self, 'Error', 'Lost connection')
            self.close()
        else:
            self.database.save_message(self.current_chat, 'out', message_text)
            logger.debug(
                f'Message sent to {self.current_chat}: {message_text}')
            self.history_list_update()

    @pyqtSlot(dict)
    def message(self, message):
        print(message)
        encrypted_message = base64.b64decode(message[MESSAGE_TEXT])
        try:
            decrypted_message = self.decrypter.decrypt(encrypted_message)
        except (ValueError, TypeError):
            self.messages.warning(
                self, 'Error', 'Decryption error.')
            return
        self.database.save_message(
            self.current_chat,
            'in',
            decrypted_message.decode('utf8'))

        sender = message[SENDER]

        if sender == self.current_chat:
            self.history_list_update()
        else:
            if self.database.check_contact(sender):
                if self.messages.question(
                    self,
                    'New message',
                    f'New message from {sender}, open chat?',
                    QMessageBox.Yes,
                        QMessageBox.No) == QMessageBox.Yes:
                    self.current_chat = sender
                    self.set_active_user()
            else:
                if self.messages.question(
                    self,
                    'New message',
                    f'New message from {sender}.\n This user not in contact list.\n Add this user to contact list?',
                    QMessageBox.Yes,
                        QMessageBox.No) == QMessageBox.Yes:
                    self.add_contact(sender)
                    self.current_chat = sender
                    self.set_active_user()

    @pyqtSlot()
    def connection_lost(self):
        self.messages.warning(self, 'Connection error', 'Lost connection. ')
        self.close()

    def make_connection(self, trans_obj):
        trans_obj.new_message.connect(self.message)
        trans_obj.lost_connection.connect(self.connection_lost)
