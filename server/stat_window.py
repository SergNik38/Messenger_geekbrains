from PyQt5.QtWidgets import QDialog, QPushButton, QTableView
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtCore import Qt


class StatWindow(QDialog):
    def __init__(self, db):
        super().__init__()

        self.db = db
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Clients statistics')
        self.setFixedSize(600, 700)
        self.setAttribute(Qt.WA_DeleteOnClose)

        self.close_button = QPushButton('Close', self)
        self.close_button.move(250, 650)
        self.close_button.clicked.connect(self.close)

        self.stat_table = QTableView(self)
        self.stat_table.move(10, 10)
        self.stat_table.setFixedSize(580, 620)

        self.create_stat_model()

    def create_stat_model(self):
        history = self.db.message_history()

        lst = QStandardItemModel()
        lst.setHorizontalHeaderLabels(['Account name', 'last logged in',
                                       'messages sent', 'messages received'])

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
        self.stat_table.setModel(lst)
        self.stat_table.resizeColumnsToContents()
        self.stat_table.resizeRowsToContents()
