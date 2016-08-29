from irods.models import User, UserGroup


class iRODSUser(object):

    def __init__(self, manager, result=None):
        self.manager = manager
        if result:
            self.id = result[User.id]
            self.name = result[User.name]
            self.type = result[User.type]
            self.zone = result[User.zone]
        self._meta = None

    def __repr__(self):
        return "<iRODSUser {id} {name} {type} {zone}>".format(**vars(self))

    def remove(self):
        self.manager.remove(self.name, self.zone)


class iRODSUserGroup(object):

    def __init__(self, manager, result=None):
        self.manager = manager
        if result:
            self.id = result[UserGroup.id]
            self.name = result[UserGroup.name]
        self._meta = None

    def __repr__(self):
        return "<iRODSUserGroup {id} {name}>".format(**vars(self))

    def remove(self):
        self.manager.remove(self.name)

    @property
    def members(self):
        return self.manager.getmembers(self.name)

    def addmember(self, user_name, user_zone=""):
        self.manager.addmember(self.name, user_name, user_zone)

    def removemember(self, user_name, user_zone=""):
        self.manager.removemember(self.name, user_name, user_zone)

    def hasmember(self, user_name):
        member_names = [user.name for user in self.members]
        return user_name in member_names
