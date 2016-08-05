class iRODSAccount(object):
    def __init__(self, host, port, user, zone, password, client_user=None, 
        client_zone=None):

        self.host = host
        self.port = port
        self.proxy_user = self.client_user = user
        self.proxy_zone = self.client_zone = zone
        self.password = password

        if client_user:
            self.client_user = client_user
            if client_zone:
                self.client_zone = client_zone
