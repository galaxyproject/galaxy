import logging
from os.path import dirname, basename

from irods.manager import Manager
from irods.message import MetadataRequest, iRODSMessage
from irods.api_number import api_number
from irods.models import (
    DataObject, Collection, Resource, User, DataObjectMeta,
                         CollectionMeta, ResourceMeta, UserMeta)
from irods.meta import iRODSMeta

logger = logging.getLogger(__name__)


class MetadataManager(Manager):

    @staticmethod
    def _model_class_to_resource_type(model_cls):
        return {
            DataObject: 'd',
            Collection: 'c',
            Resource: 'r',
            User: 'u',
        }[model_cls]

    def get(self, model_cls, path):
        resource_type = self._model_class_to_resource_type(model_cls)
        model = {
            'd': DataObjectMeta,
            'c': CollectionMeta,
            'r': ResourceMeta,
            'u': UserMeta
        }[resource_type]
        conditions = {
            'd': [
                Collection.name == dirname(path),
                DataObject.name == basename(path)
            ],
            'c': [Collection.name == path],
            'r': [Resource.name == path],
            'u': [User.name == path]
        }[resource_type]
        results = self.sess.query(model.id, model.name, model.value, model.units)\
            .filter(*conditions).all()
        return [iRODSMeta(
            row[model.name],
            row[model.value],
            row[model.units],
            id=row[model.id]
        ) for row in results]

    def add(self, model_cls, path, meta):
        resource_type = self._model_class_to_resource_type(model_cls)
        message_body = MetadataRequest(
            "add",
            "-" + resource_type,
            path,
            meta.name,
            meta.value,
            meta.units
        )
        request = iRODSMessage("RODS_API_REQ", msg=message_body,
                               int_info=api_number['MOD_AVU_METADATA_AN'])
        with self.sess.pool.get_connection() as conn:
            conn.send(request)
            response = conn.recv()
        logger.debug(response.int_info)

    def remove(self, model_cls, path, meta):
        resource_type = self._model_class_to_resource_type(model_cls)
        message_body = MetadataRequest(
            "rm",
            "-" + resource_type,
            path,
            meta.name,
            meta.value,
            meta.units
        )
        request = iRODSMessage("RODS_API_REQ", msg=message_body,
                               int_info=api_number['MOD_AVU_METADATA_AN'])
        with self.sess.pool.get_connection() as conn:
            conn.send(request)
            response = conn.recv()
        logger.debug(response.int_info)

    def copy(self, src_model_cls, dest_model_cls, src, dest):
        src_resource_type = self._model_class_to_resource_type(src_model_cls)
        dest_resource_type = self._model_class_to_resource_type(dest_model_cls)
        message_body = MetadataRequest(
            "cp",
            "-" + src_resource_type,
            "-" + dest_resource_type,
            src,
            dest
        )
        request = iRODSMessage("RODS_API_REQ", msg=message_body,
                               int_info=api_number['MOD_AVU_METADATA_AN'])

        with self.sess.pool.get_connection() as conn:
            conn.send(request)
            response = conn.recv()
        logger.debug(response.int_info)

    def set(self, model_cls, path, meta):
        resource_type = self._model_class_to_resource_type(model_cls)
        message_body = MetadataRequest(
            "set",
            "-" + resource_type,
            path,
            meta.name,
            meta.value,
            meta.units
        )
        request = iRODSMessage("RODS_API_REQ", msg=message_body,
                               int_info=api_number['MOD_AVU_METADATA_AN'])
        with self.sess.pool.get_connection() as conn:
            conn.send(request)
            response = conn.recv()
        logger.debug(response.int_info)
