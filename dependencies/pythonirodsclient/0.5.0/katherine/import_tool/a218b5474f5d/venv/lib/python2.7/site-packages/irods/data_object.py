from os import O_RDONLY, O_WRONLY, O_RDWR
from io import RawIOBase, BufferedRandom
import sys

from irods.models import DataObject
from irods.meta import iRODSMetaCollection


class iRODSReplica(object):
    def __init__(self, status, resource_name, path):
        self.status = status
        self.resource_name = resource_name
        self.path = path

    def __repr__(self):
        return "<{0}.{1} {2}>".format(
            self.__class__.__module__,
            self.__class__.__name__,
            self.resource_name
        )

class iRODSDataObject(object):
    def __init__(self, manager, parent=None, results=None):
        self.manager = manager
        if parent and results:
            self.collection = parent
            for attr, value in DataObject.__dict__.iteritems():
                if not attr.startswith('_'):
                    try:
                        setattr(self, attr, results[0][value])
                    except KeyError:
                        # backward compatibility with pre iRODS 4
                        sys.exc_clear()
            self.path = self.collection.path + '/' + self.name
            replicas = sorted(results, key=lambda r: r[DataObject.replica_number])
            self.replicas = [iRODSReplica(
                r[DataObject.replica_status],
                r[DataObject.resource_name],
                r[DataObject.path]
            ) for r in replicas]
        self._meta = None

    def __repr__(self):
        return "<iRODSDataObject {id} {name}>".format(id=self.id, name=self.name.encode('utf-8'))

    @property
    def metadata(self):
        if not self._meta:
            self._meta = iRODSMetaCollection(self.manager.sess.metadata, DataObject, self.path)
        return self._meta

    def open(self, mode='r'):
        flag, create_if_not_exists, seek_to_end = {
            'r': (O_RDONLY, False, False),
            'r+': (O_RDWR, False, False),
            'w': (O_WRONLY, True, False),
            'w+': (O_RDWR, True, False),
            'a': (O_WRONLY, True, True),
            'a+': (O_RDWR, True, True),
        }[mode]
        # TODO: Actually use create_if_not_exists and seek_to_end
        conn, desc = self.manager.open(self.path, flag)
        return BufferedRandom(iRODSDataObjectFileRaw(conn, desc))

    def unlink(self, force=False):
        self.manager.unlink(self.path, force)

    def truncate(self, size):
        self.manager.truncate(self.path, size)

class iRODSDataObjectFileRaw(RawIOBase):
    def __init__(self, conn, descriptor):
        self.conn = conn
        self.desc = descriptor

    def close(self):
        self.conn.close_file(self.desc)
        self.conn.release()
        super(iRODSDataObjectFileRaw, self).close()
        return None

    def seek(self, offset, whence=0):
        return self.conn.seek_file(self.desc, offset, whence)

    def readinto(self, b):
        contents = self.conn.read_file(self.desc, len(b))
        if contents is None:
            return 0
        for i, c in enumerate(contents):
            b[i] = c
        return len(contents)

    def write(self, b):
        return self.conn.write_file(self.desc, str(b.tobytes()))

    def readable(self):
        return True

    def writable(self):
        return True

    def seekable(self):
        return True
