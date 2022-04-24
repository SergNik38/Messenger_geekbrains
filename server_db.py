from sqlalchemy import create_engine, Table, Column, Integer, \
    String, MetaData, ForeignKey, DateTime
from sqlalchemy.orm import mapper, sessionmaker
from common.const import *
import datetime


class ServerStorage:
    class AllUsers:
        def __init__(self, username):
            self.name = username
            self.last_login = datetime.datetime.now()
            self.id = None

    class ActiveUsers:
        def __init__(self, user_id, ip_address, port, login_time):
            self.user = user_id
            self.ip = ip_address
            self.port = port
            self.login_time = login_time
            self.id = None

    class LoginHistory:
        def __init__(self, name, date, ip, port):
            self.id = None
            self.name = name
            self.date = date
            self.ip = ip
            self.port = port

    class UsersContacts:
        def __init__(self, user, contact):
            self.id = None
            self.user = user
            self.contact = contact

    class UsersHistory:
        def __init__(self, user):
            self.id = None
            self.user = user
            self.sent = 0
            self.accepted = 0

    def __init__(self, path):
        self.db_engine = create_engine(f'sqlite:///{path}', echo=False, pool_recycle=7200,
                                       connect_args={'check_same_thread': False})
        self.metadata = MetaData()

        users = Table('Users', self.metadata,
                      Column('id', Integer, primary_key=True),
                      Column('name', String, unique=True),
                      Column('last_login', DateTime))

        active_users = Table('ActiveUsers', self.metadata,
                             Column('id', Integer, primary_key=True),
                             Column('user', ForeignKey('Users.id')),
                             Column('login_time', DateTime),
                             Column('ip', String),
                             Column('port', String))

        login_history = Table('LoginHistory', self.metadata,
                              Column('id', Integer, primary_key=True),
                              Column('name', ForeignKey('Users.id')),
                              Column('date', DateTime),
                              Column('ip', String),
                              Column('port', String))

        users_contacts = Table('UsersContacts', self.metadata,
                               Column('id', Integer, primary_key=True),
                               Column('user', ForeignKey('Users.id')),
                               Column('contact', ForeignKey('Users.id')))

        users_history = Table('UsersHistory', self.metadata,
                              Column('id', Integer, primary_key=True),
                              Column('user', ForeignKey('Users.id')),
                              Column('sent', Integer),
                              Column('accepted', Integer))

        self.metadata.create_all(self.db_engine)

        mapper(self.AllUsers, users)
        mapper(self.ActiveUsers, active_users)
        mapper(self.LoginHistory, login_history)
        mapper(self.UsersContacts, users_contacts)
        mapper(self.UsersHistory, users_history)

        Session = sessionmaker(bind=self.db_engine)
        self.session = Session()

        self.session.query(self.ActiveUsers).delete()
        self.session.commit()

    def user_login(self, username, ip, port):
        res = self.session.query(self.AllUsers).filter_by(name=username)

        if res.count():
            user = res.first()
            user.last_login = datetime.datetime.now()
        else:
            user = self.AllUsers(username)
            self.session.add(user)
            self.session.commit()
            user_history = self.UsersHistory(user.id)
            self.session.add(user_history)

        new_active_user = self.ActiveUsers(user.id, ip, port, datetime.datetime.now())
        self.session.add(new_active_user)

        history = self.LoginHistory(user.id, datetime.datetime.now(), ip, port)
        self.session.add(history)

        self.session.commit()

    def user_logout(self, username):
        user = self.session.query(self.AllUsers).filter_by(name=username).first()
        self.session.query(self.ActiveUsers).filter_by(user=user.id).delete()
        self.session.commit()

    def message_handler(self, sender, recipient):
        sender = self.session.query(self.AllUsers).filter_by(name=sender).first().id
        recipient = self.session.query(self.AllUsers).filter_by(name=recipient).first().id

        sender_row = self.session.query(self.UsersHistory).filter_by(user=sender).first()
        sender_row.sent += 1

        recipient_row = self.session.query(self.UsersHistory).filter_by(user=recipient).first()
        recipient_row.accpted += 1

        self.session.commit()

    def add_contact(self, user, contact):
        user = self.session.query(self.AllUsers).filter_by(name=user).first()
        contact = self.session.query(self.AllUsers).filter_by(name=contact).first()

        if not contact or self.session.query(self.UsersContacts).filter_by(user=user.id, contact=contact.id).count():
            return

        contact_row = self.UsersContacts(user.id, contact.id)
        self.session.add(contact_row)
        self.session.commit()

    def del_contact(self, user, contact):
        user = self.session.query(self.AllUsers).filter_by(name=user).first()
        contact = self.session.query(self.AllUsers).filter_by(name=contact).first()

        if not contact:
            return

        self.session.query(self.UsersContacts).filter(
            self.UsersContacts.user == user.id,
            self.UsersContacts.contact == contact.id
        ).delete()
        self.session.commit()

    def get_contacts(self, user):
        user = self.session.query(self.AllUsers).filter_by(name=user).one()
        query = self.session.query(self.UsersContacts, self.AllUsers.name).filter_by(user=user.id). \
            join(self.AllUsers, self.UsersContacts.contact == self.AllUsers.id)

        return [contact[1] for contact in query.all()]

    def message_history(self):
        query = self.session.query(
            self.AllUsers.name,
            self.AllUsers.last_login,
            self.UsersHistory.sent,
            self.UsersHistory.accepted
        ).join(self.AllUsers)
        return query.all()

    def list_users(self):
        query = self.session.query(
            self.AllUsers.name,
            self.AllUsers.last_login,
        )
        return query.all()

    def list_active_users(self):
        query = self.session.query(
            self.AllUsers.name,
            self.ActiveUsers.ip,
            self.ActiveUsers.port,
            self.ActiveUsers.login_time,
        ).join(self.AllUsers)
        return query.all()

    def login_history(self, username=None):
        query = self.session.query(
            self.AllUsers.name,
            self.LoginHistory.date,
            self.LoginHistory.ip,
            self.LoginHistory.port,
        ).join(self.AllUsers)
        return query.all()


if __name__ == '__main__':
    test_db = ServerStorage()

    test_db.user_login('test_client_1', '192.168.1.8', 8080)
    test_db.user_login('test_client_2', '192.168.1.9', 8081)

    print(test_db.list_active_users())

    test_db.user_logout('test_client_1')

    print(test_db.list_active_users())

    test_db.login_history('test_client_1')

    print(test_db.list_users())
