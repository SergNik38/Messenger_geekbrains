# Default server port
DEFAULT_PORT = 8888

# Default server IP
DEFAULT_IP_ADDRESS = '127.0.0.1'

# Maximum connections
MAX_CONNECTIONS = 5

# Max length of package
MAX_PACKAGE_LENGTH = 1024

# Default encoding
ENCODING = 'utf-8'

# Default JIM Protocol
ACTION = 'action'
TIME = 'time'
USER = 'user'
ACCOUNT_NAME = 'account_name'
DESTINATION = 'to'
SENDER = 'from'

# Other
PRESENCE = 'presence'
RESPONSE = 'response'
ERROR = 'error'
MESSAGE = 'msg'
MESSAGE_TEXT = 'msg txt'
EXIT = 'exit'
GET_CONTACTS = 'get contacts'
ADD_CONTACT = 'add contact'
REMOVE_CONTACT = 'remove contact'
USERS_REQUEST = 'get users'
LIST_INFO = 'data list'

# DB
SERVER_DATABASE = 'sqlite:///server_base.db3'

# RESPONSE
RESPONSE_202 = {
    RESPONSE: 202,
    LIST_INFO: None
}
RESPONSE_200 = {
    RESPONSE: 200
}
