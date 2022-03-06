import unittest
import json
from common.const import RESPONSE, ERROR, USER, ACCOUNT_NAME, TIME, ACTION, PRESENCE, ENCODING
from common.utils import get_message, send_message


class TestSocket:
    def __init__(self, test_dict):
        self.test_dict = test_dict
        self.enc_msg = None
        self.recv_msg = None

    def send(self, seng_msg):
        json_test_msg = json.dumps(self.test_dict)
        self.enc_msg = json_test_msg.encode(ENCODING)
        self.recv_msg = seng_msg

    def recv(self, length):
        json_test_msg = json.dumps(self.test_dict)
        return json_test_msg.encode(ENCODING)


class TestUtils(unittest.TestCase):
    test_dict_send = {
        ACTION: PRESENCE,
        TIME: 2,
        USER: {
            ACCOUNT_NAME: 'TestUser'
        }
    }
    test_recv_dict_ok = {RESPONSE: 200}
    test_recv_dict_err = {RESPONSE: 400,
                          ERROR: 'BAD REQUEST'}

    def test_dict_msg(self):
        test_sock = TestSocket(self.test_dict_send)
        send_message(test_sock, self.test_dict_send)
        self.assertEqual(test_sock.enc_msg, test_sock.recv_msg)
        with self.assertRaises(Exception):
            send_message(test_sock, test_sock)

    def test_get_msg(self):
        test_sock_ok = TestSocket(self.test_recv_dict_ok)
        test_sock_err = TestSocket(self.test_recv_dict_err)

        self.assertEqual(get_message(test_sock_ok), self.test_recv_dict_ok)
        self.assertEqual(get_message(test_sock_err), self.test_recv_dict_err)


if __name__ == '__main__':
    unittest.main()