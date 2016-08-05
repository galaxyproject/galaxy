from os.path import basename, dirname

from irods.manager import Manager
from irods.api_number import api_number
from irods.message import ModAclRequest, iRODSMessage
from irods.data_object import iRODSDataObject
from irods.collection import iRODSCollection
from irods.models import (
    DataObject, Collection, User, DataAccess, CollectionAccess, CollectionUser)
from irods.access import iRODSAccess

import logging

logger = logging.getLogger(__name__)


class AccessManager(Manager):

    def get(self, target):
        # different query whether target is an object or a collection
        if type(target) == iRODSDataObject:
            access_type = DataAccess
            user_type = User
            conditions = [
                Collection.name == dirname(target.path),
                DataObject.name == basename(target.path)
            ]
        elif type(target) == iRODSCollection:
            access_type = CollectionAccess
            user_type = CollectionUser
            conditions = [
                Collection.name == target.path
            ]
        else:
            raise TypeError

        results = self.sess.query(user_type.name, user_type.zone, access_type.name)\
            .filter(*conditions).all()

        return [iRODSAccess(
            access_name=row[access_type.name],
            user_name=row[user_type.name],
            path=target.path,
            user_zone=row[user_type.zone]
        ) for row in results]

    def set(self, acl, recursive=False):
        message_body = ModAclRequest(
            recursiveFlag=int(recursive),
            accessLevel=acl.access_name,
            userName=acl.user_name,
            zone=acl.user_zone,
            path=acl.path
        )
        request = iRODSMessage("RODS_API_REQ", msg=message_body,
                               int_info=api_number['MOD_ACCESS_CONTROL_AN'])
        with self.sess.pool.get_connection() as conn:
            conn.send(request)
            response = conn.recv()
        logger.debug(response.int_info)
