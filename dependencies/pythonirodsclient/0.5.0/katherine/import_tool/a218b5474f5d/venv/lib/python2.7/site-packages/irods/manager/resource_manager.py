from irods.models import Resource
from irods.manager import Manager
from irods.message import GeneralAdminRequest, iRODSMessage
from irods.exception import ResourceDoesNotExist, NoResultFound
from irods.api_number import api_number
from irods.resource import iRODSResource

import logging

logger = logging.getLogger(__name__)


class ResourceManager(Manager):

    def get(self, name, zone=""):
        query = self.sess.query(Resource).filter(Resource.name == name)

        if len(zone) > 0:
            query = query.filter(Resource.zone_name == zone)

        try:
            result = query.one()
        except NoResultFound:
            raise ResourceDoesNotExist()
        return iRODSResource(self, result)

    def create(self, name, resource_type, host, path, context="", zone="", resource_class=""):
        with self.sess.pool.get_connection() as conn:
            # check server version
            server_version = tuple(int(token)
                                   for token in conn.server_version.replace('rods', '').split('.'))
            if server_version < (4, 0, 0):
                # make resource, iRODS 3 style
                message_body = GeneralAdminRequest(
                    "add",
                    "resource",
                    name,
                    resource_type,
                    resource_class,
                    host,
                    path,
                    zone
                )
            else:
                message_body = GeneralAdminRequest(
                    "add",
                    "resource",
                    name,
                    resource_type,
                    host + ":" + path,
                    context,
                    zone
                )

            request = iRODSMessage("RODS_API_REQ", msg=message_body,
                                   int_info=api_number['GENERAL_ADMIN_AN'])

            conn.send(request)
            response = conn.recv()
            self.sess.cleanup()
                              # close connections to get new agents with up to
                              # date resource manager
        logger.debug(response.int_info)

    def remove(self, name, test=False):
        if test:
            mode = "--dryrun"
        else:
            mode = ""
        message_body = GeneralAdminRequest(
            "rm",
            "resource",
            name,
            mode
        )
        request = iRODSMessage("RODS_API_REQ", msg=message_body,
                               int_info=api_number['GENERAL_ADMIN_AN'])
        with self.sess.pool.get_connection() as conn:
            conn.send(request)
            response = conn.recv()
            self.sess.cleanup()
                              # close connections to get new agents with up to
                              # date resource manager
        logger.debug(response.int_info)
