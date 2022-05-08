from PyQt5.QtWidgets import QMainWindow, QAction, qApp, QApplication, QLabel, QTableView
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtCore import QTimer
from server.stat_window import StatWindow
from server.config_window import ConfigWindow
from server.add_user import RegisterUser
from server.remove_user import DeleteUserDialog


class MainWindow(QMainWindow):
    """Main GUI server window"""
    def __init__(self, db, server, config):
        super().__init__()
        self.db = db

        self.server_thread = server
        self.config = config

        exitAction = QAction('Exit', self)
        exitAction.setShortcut('Command+Q')
        exitAction.triggered.connect(qApp.quit)

        self.refresh_btn = QAction('Refresh list', self)

        self.config_btn = QAction('Server settings', self)

        self.show_history_btn = QAction('Clients history', self)

        self.register_btn = QAction('Register user', self)

        self.remove_btn = QAction('Delete user', self)

        self.statusBar()

        self.toolbar = self.addToolBar('MainBar')
        self.toolbar.addAction(exitAction)
        self.toolbar.addAction(self.refresh_btn)
        self.toolbar.addAction(self.config_btn)
        self.toolbar.addAction(self.show_history_btn)
        self.toolbar.addAction(self.register_btn)
        self.toolbar.addAction(self.remove_btn)

        self.setFixedSize(800, 600)
        self.setWindowTitle('Messaging server prealpha release')

        self.label = QLabel('Connected clients', self)
        self.label.setFixedSize(240, 15)
        self.label.move(10, 25)

        self.active_clients = QTableView(self)
        self.active_clients.move(10, 45)
        self.active_clients.setFixedSize(780, 400)

        self.timer = QTimer()
        self.timer.timeout.connect(self.create_user_model)
        self.timer.start(1000)

        self.refresh_btn.triggered.connect(self.create_user_model)
        self.show_history_btn.triggered.connect(self.show_statistics)
        self.config_btn.triggered.connect(self.server_config)
        self.register_btn.triggered.connect(self.reg_user)
        self.remove_btn.triggered.connect(self.rem_user)
        self.show()

    def create_user_model(self):
        users_list = self.db.list_active_users()
        lst = QStandardItemModel()
        lst.setHorizontalHeaderLabels(
            ['Account name', 'IP address', 'Port', 'Connection time'])
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
        self.active_clients.setModel(lst)
        self.active_clients.resizeColumnsToContents()
        self.active_clients.resizeRowsToContents()

    def show_statistics(self):
        global stat_window
        stat_window = StatWindow(self.db)
        stat_window.show()

    def server_config(self):
        global config_window
        config_window = ConfigWindow(self.config)

    def reg_user(self):
        global reg_window
        reg_window = RegisterUser(self.db, self.server_thread)
        reg_window.show()

    def rem_user(self):
        global rem_window
        rem_window = DeleteUserDialog(self.db, self.server_thread)
        rem_window.show()
