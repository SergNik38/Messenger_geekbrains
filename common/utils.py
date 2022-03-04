import json
from .const import MAX_PACKAGE_LENGTH, ENCODING


def get_message(client):
    """ receiving message
    :param client:
    :return
    """
    response_bytes = client.recv(MAX_PACKAGE_LENGTH)
    if isinstance(response_bytes, bytes):
        json_response = response_bytes.decode(ENCODING)
        response = json.loads(json_response)
        if isinstance(response, dict):
            return response
        raise ValueError
    raise ValueError


def send_message(sock, message):
    """
    sending messages
    :param sock:
    :param message:
    :return:
    """
    json_message = json.dumps(message)
    message_bytes = json_message.encode(ENCODING)
    sock.send(message_bytes)
