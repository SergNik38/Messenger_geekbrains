import unittest
from common.const import RESPONSE, ERROR, USER, ACCOUNT_NAME, TIME, ACTION, PRESENCE
from client import Client


class TestClient(unittest.TestCase):
    client = Client()

    def test_presence(self):
        test = self.client.create_presence()
        test[TIME] = 2
        self.assertEqual(test, {ACTION: PRESENCE, TIME: 2, USER: {ACCOUNT_NAME: 'Guest'}})

    def test_200(self):
        self.assertEqual(self.client.answer_handler({RESPONSE: 200}), 'OK')

    def test_400(self):
        self.assertEqual(self.client.answer_handler({RESPONSE: 400, ERROR: 'Bad Request'}), '400 : Bad Request')

    def test_no_response(self):
        self.assertRaises(ValueError, self.client.answer_handler, {ERROR: 'Bad Request'})


if __name__ == '__main__':
    unittest.main()
