import sys
from PyQt5.QtWidgets import QMainWindow, QAction, qApp, QApplication, QLabel, QTableView, QDialog, QPushButton, \
    QLineEdit, QFileDialog, QMessageBox
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtCore import Qt


def gui_create_model(db):
    users_list = db.list_active_users()
    lst = QStandardItemModel()
    lst.setHorizontalHeaderLabels(['Account name', 'IP address', 'Port', 'Connection time'])
    for row in users_list:
        user, ip, port, time = row
        user = QStandardItem(user)
        user.setEditable(False)
        ip = QStandardItem(ip)
        ip.setEditable(False)
        port = QStandardItem(str(port))
        port.setEditable(False)
        time = QStandardItem(str(time.replace(microsecond=0)))
        time.setEditable(False)
        lst.appendRow([user, ip, port, time])
    return lst


def create_stat_model(db):
    history = db.message_history()

    lst = QStandardItemModel()
    lst.setHorizontalHeaderLabels(['Account name', 'last logged in', 'messages sent', 'messages received'])

    for row in history:
        user, last_logged, sent, received = row
        user = QStandardItem(user)
        user.setEditable(False)
        last_logged = QStandardItem(str(last_logged.replace(microsecond=0)))
        last_logged.setEditable(False)
        sent = QStandardItem(str(sent))
        sent.setEditable(False)
        received = QStandardItem(str(received))
        received.setEditable(False)
        lst.appendRow([user, last_logged, sent, received])
    return lst


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        exitAction = QAction('Exit', self)
        exitAction.setShortcut('Command+Q')
        exitAction.triggered.connect(qApp.quit)

        self.refresh_btn = QAction('Refresh list', self)

        self.config_btn = QAction('Server settings', self)

        self.show_history_btn = QAction('Clients history', self)

        self.statusBar()

        self.toolbar = self.addToolBar('MainBar')
        self.toolbar.addAction(exitAction)
        self.toolbar.addAction(self.refresh_btn)
        self.toolbar.addAction(self.config_btn)
        self.toolbar.addAction(self.show_history_btn)

        self.setFixedSize(800, 600)
        self.setWindowTitle('Messaging server prealpha release')

        self.label = QLabel('Connected clients', self)
        self.label.setFixedSize(240, 15)
        self.label.move(10, 25)

        self.active_clients = QTableView(self)
        self.active_clients.move(10, 45)
        self.active_clients.setFixedSize(780, 400)

        self.show()


class HistoryWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Clients statistics')
        self.setFixedSize(600, 700)
        self.setAttribute(Qt.WA_DeleteOnClose)

        self.close_btn = QPushButton('Close', self)
        self.close_btn.move(250, 650)
        self.close_btn.clicked.connect(self.close)

        self.history = QTableView(self)
        self.history.move(10, 10)
        self.history.setFixedSize(580, 620)

        self.show()


class ConfigWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setFixedSize(365, 260)
        self.setWindowTitle('Server settings')

        self.db_path_label = QLabel('Database path: ', self)
        self.db_path_label.move(10, 10)
        self.db_path_label.setFixedSize(240, 15)

        self.db_path = QLineEdit(self)
        self.db_path.setFixedSize(250, 20)
        self.db_path.move(10, 30)
        self.db_path.setReadOnly(True)

        self.db_path_select = QPushButton('Path...', self)
        self.db_path_select.move(275, 28)

        def open_file_dialog():
            global dialog
            dialog = QFileDialog(self)
            path = dialog.getExistingDirectory()
            self.db_path.insert(path)

        self.db_path_select.clicked.connect(open_file_dialog)

        self.db_file_label = QLabel('Database filename: ', self)
        self.db_file_label.move(10, 68)
        self.db_file_label.setFixedSize(180, 15)

        self.db_file = QLineEdit(self)
        self.db_file.move(200, 66)
        self.db_file.setFixedSize(150, 20)

        self.port_label = QLabel('Port: ', self)
        self.port_label.move(10, 108)
        self.port_label.setFixedSize(180, 15)

        self.port = QLineEdit(self)
        self.port.move(200, 108)
        self.port.setFixedSize(150, 20)

        self.ip_label = QLabel('IP address: ', self)
        self.ip_label.move(10, 148)
        self.ip_label.setFixedSize(180, 15)

        self.ip_label_note = QLabel(' leave this field empty\n to accept connections from any IP address', self)
        self.ip_label_note.move(10, 168)
        self.ip_label_note.setFixedSize(500, 30)

        self.ip = QLineEdit(self)
        self.ip.move(200, 148)
        self.ip.setFixedSize(150, 20)

        self.save_btn = QPushButton('Save', self)
        self.save_btn.move(190, 220)

        self.close_button = QPushButton('Close', self)
        self.close_button.move(275, 220)
        self.close_button.clicked.connect(self.close)

        self.show()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    message = QMessageBox
    dial = ConfigWindow()

    app.exec_()
