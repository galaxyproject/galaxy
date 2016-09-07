import sys
from irods.models import Resource


class iRODSResource(object):

    def __init__(self, manager, result=None):
        self.manager = manager
        if result:
            '''
            self.id = result[Resource.id]
            self.name = result[Resource.name]
            self.zone_name = result[Resource.zone_name]
            self.type = result[Resource.type]
            self.class_name = result[Resource.class_name]
            self.location = result[Resource.location]
            self.vault_path = result[Resource.vault_path]
            self.free_space = result[Resource.free_space]
            self.free_space_time = result[Resource.free_space_time]
            self.comment = result[Resource.comment]
            self.create_time = result[Resource.create_time]
            self.modify_time = result[Resource.modify_time]
            self.status = result[Resource.status]
            self.children = result[Resource.children]
            self.context = result[Resource.context]
            self.parent = result[Resource.parent]
            self.obj_count = result[Resource.obj_count]
            '''
            for attr, value in Resource.__dict__.iteritems():
                if not attr.startswith('_'):
                    try:
                        setattr(self, attr, result[value])
                    except KeyError:
                        # backward compatibility with pre iRODS 4
                        sys.exc_clear()

        self._meta = None

    def __repr__(self):
        return "<iRODSResource {id} {name} {type}>".format(**vars(self))
