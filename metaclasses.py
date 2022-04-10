import dis


class ServerMaker(type):
    def __init__(self, clsname, bases, clsdict):
        methods = []

        for func in clsdict:
            try:
                res = dis.get_instructions(clsdict[func])
            except TypeError:
                pass
            else:
                for el in res:
                    if el.opname == 'LOAD_GLOBAL':
                        if el.argval not in methods:
                            methods.append(el.argval)
        if 'connect' in methods:
            raise TypeError('Method "connect" is not allowed in Server class')
        super().__init__(clsname, bases, clsdict)


class ClientMaker(type):
    def __init__(self, clsname, bases, clsdict):
        methods = []
        for func in clsdict:
            try:
                res = dis.get_instructions(clsdict[func])
            except TypeError:
                pass
            else:
                for el in res:
                    if el.opname == 'LOAD_GLOBAL':
                        if el.argval not in methods:
                            methods.append(el.argval)
            for command in ('accept', 'listen'):
                if command in methods:
                    raise TypeError('Incorrect method in Client class')
        super().__init__(clsname, bases, clsdict)
