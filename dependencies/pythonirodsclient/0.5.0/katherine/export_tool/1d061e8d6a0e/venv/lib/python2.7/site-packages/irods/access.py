class iRODSAccess(object):

    def __init__(self, access_name, path, user_name, user_zone=''):
        self.access_name = access_name
        self.path = path
        self.user_name = user_name
        self.user_zone = user_zone

    def __repr__(self):
        return "<iRODSAccess {access_name} {path} {user_name} {user_zone}>".format(**vars(self))
