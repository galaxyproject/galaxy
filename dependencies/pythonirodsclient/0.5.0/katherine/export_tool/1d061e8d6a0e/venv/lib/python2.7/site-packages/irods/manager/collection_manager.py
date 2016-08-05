from irods.models import Collection
from irods.manager import Manager
from irods.message import iRODSMessage, CollectionRequest, FileOpenRequest, ObjCopyRequest, StringStringMap
from irods.exception import CollectionDoesNotExist, NoResultFound
from irods.api_number import api_number
from irods.collection import iRODSCollection
from irods.constants import SYS_SVR_TO_CLI_COLL_STAT, SYS_CLI_TO_SVR_COLL_STAT_REPLY


class CollectionManager(Manager):
    def get(self, path):
        query = self.sess.query(Collection).filter(Collection.name == path)
        try:
            result = query.one()
        except NoResultFound:
            raise CollectionDoesNotExist()
        return iRODSCollection(self, result)
            
    def create(self, path):
        message_body = CollectionRequest(
            collName=path,
            KeyValPair_PI=StringStringMap()
        )
        message = iRODSMessage('RODS_API_REQ', msg=message_body, 
            int_info=api_number['COLL_CREATE_AN'])
        with self.sess.pool.get_connection() as conn:
            conn.send(message)
            response = conn.recv()
        return self.get(path)

    def remove(self, path, recurse=True, force=False, additional_flags={}):
        options = {}
        if recurse:
            options['recursiveOpr'] = ''
        if force:
            options['forceFlag'] = ''
        options = dict(options.items() + additional_flags.items())
        message_body = CollectionRequest(
            collName=path,
            KeyValPair_PI=StringStringMap(options)
        )
        message = iRODSMessage('RODS_API_REQ', msg=message_body,
            int_info=api_number['RM_COLL_AN'])
        with self.sess.pool.get_connection() as conn:
            conn.send(message)
            response = conn.recv()
            
            while response.int_info == SYS_SVR_TO_CLI_COLL_STAT:
                conn.reply(SYS_CLI_TO_SVR_COLL_STAT_REPLY)
                response = conn.recv()

    def exists(self, path):
        try:
            self.get(path)
        except CollectionDoesNotExist:
            return False
        return True

    def move(self, src_path, dest_path):
        # check if dest is an existing collection
        # if so append collection name to it
        if self.sess.collections.exists(dest_path):
            coll_name = src_path.rsplit('/',1)[1]
            target_path = dest_path + '/' + coll_name
        else:
            target_path = dest_path

        src = FileOpenRequest(
            objPath=src_path,
            createMode=0,
            openFlags=0,
            offset=0,
            dataSize=0,
            numThreads=0,
            oprType=12,   # RENAME_COLL
            KeyValPair_PI=StringStringMap(),
        )
        dest = FileOpenRequest(
            objPath=target_path,
            createMode=0,
            openFlags=0,
            offset=0,
            dataSize=0,
            numThreads=0,
            oprType=12,   # RENAME_COLL
            KeyValPair_PI=StringStringMap(),
        )
        message_body = ObjCopyRequest(
            srcDataObjInp_PI = src,
            destDataObjInp_PI = dest
        )
        message = iRODSMessage('RODS_API_REQ', msg=message_body,
            int_info=api_number['DATA_OBJ_RENAME_AN'])

        with self.sess.pool.get_connection() as conn:
            conn.send(message)
            response = conn.recv()



