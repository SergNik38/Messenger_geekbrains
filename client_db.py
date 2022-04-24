from sqlalchemy import create_engine, Table, Column, Integer, String, Text, MetaData, DateTime
from sqlalchemy.orm import mapper, sessionmaker
from common.const import *
import datetime


class ClientDatabase:
    class KnownUsers:
        def __init__(self, user):
            self.id = None
            self.user = user

    class MessageHistory:
        def __init__(self, from_user, to_user, message):
            self.id = None
            self.from_user = from_user
            self.to_user = to_user
            self.message = message
            self.date = datetime.datetime.now()

    class Contacts:
        def __init__(self, contact):
            self.id = None
            self.contact = contact

    def __init__(self, client_name):
        self.db_engine = create_engine(f'sqlite:///client_{client_name}.db3', echo=False,
                                       pool_recycle=7200)

        self.metadata = MetaData()

        known_users = Table('KnownUsers', self.metadata,
                            Column('id', Integer, primary_key=True),
                            Column('user', String))

        message_history = Table('MessageHistory', self.metadata,
                                Column('id', Integer, primary_key=True),
                                Column('from_user', String),
                                Column('to_user', String),
                                Column('message', Text),
                                Column('date', DateTime))

        contacts = Table('Contacts', self.metadata,
                         Column('id', Integer, primary_key=True),
                         Column('contact', String, unique=True))

        self.metadata.create_all(self.db_engine)

        mapper(self.KnownUsers, known_users)
        mapper(self.MessageHistory, message_history)
        mapper(self.Contacts, contacts)

        Session = sessionmaker(bind=self.db_engine)

        self.session = Session()

        self.session.query(self.Contacts).delete()
        self.session.commit()

    def add_contact(self, contact):
        if not self.session.query(self.Contacts).filter_by(contact=contact).count():
            contact_row = self.Contacts(contact)
            self.session.add(contact_row)
            self.session.commit()

    def delete_contact(self, contact):
        self.session.query(self.Contacts).filter_by(contact=contact).delete()

    def add_users(self, users_list):
        self.session.query(self.KnownUsers).delete()
        for user in users_list:
            user_row = self.KnownUsers(user)
            self.session.add(user_row)
        self.session.commit()

    def save_message(self, from_user, to_user, message):
        message_row = self.MessageHistory(from_user, to_user, message)
        self.session.add(message_row)
        self.session.commit()

    def get_contacts(self):
        return [contact[0] for contact in self.session.query(self.Contacts.contact).all()]

    def get_users(self):
        return [user[0] for user in self.session.query(self.KnownUsers.user).all()]

    def check_user(self, user):
        if self.session.query(self.KnownUsers).filter_by(user=user).count():
            return True
        else:
            return False

    def check_contact(self, contact):
        if self.session.query(self.Contacts).filter_by(contact=contact).count():
            return True
        else:
            return False

    def get_history(self, from_user=None, to_user=None):
        query = self.session.query(self.MessageHistory)
        if from_user:
            query = query.filter_by(from_user=from_user)
        if to_user:
            query = query.filter_by(to_user=to_user)

        return [(history_row.from_user, history_row.to_user, history_row.message, history_row.date)
                for history_row in query.all()]


if __name__ == '__main__':
    test_db = ClientDatabase('test1')
    for i in ['test3', 'test4', 'test5']:
        test_db.add_contact(i)
    test_db.add_contact('test4')
    test_db.add_users(['test1', 'test2', 'test3', 'test4', 'test5'])
    test_db.save_message('test1', 'test2', f'Test message from {datetime.datetime.now()}!')
    test_db.save_message('test2', 'test1', f'Another test message from {datetime.datetime.now()}!')
    print(test_db.get_contacts())
    print(test_db.get_users())
    print(test_db.check_user('test1'))
    print(test_db.check_user('test10'))
    print(test_db.get_history('test2'))
    print(test_db.get_history(to_user='test2'))
    print(test_db.get_history('test3'))
    test_db.delete_contact('test4')
    print(test_db.get_contacts())

