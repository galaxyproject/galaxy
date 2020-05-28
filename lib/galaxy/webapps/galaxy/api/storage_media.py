"""
API operations on storage media.

.. see also:: :class:`galaxy.model.StorageMedia`
"""
import logging
import os

from galaxy import exceptions
from galaxy.managers import (
    datasets,
    hdas,
    storage_media,
    users
)
from galaxy.util import (
    string_as_bool,
    unicodify
)
from galaxy.web import expose_api
from galaxy.webapps.base.controller import BaseAPIController

log = logging.getLogger(__name__)


class StorageMediaController(BaseAPIController):
    """
    RESTful controller for interactions with storage media.
    """

    def __init__(self, app):
        super(StorageMediaController, self).__init__(app)
        self.user_manager = users.UserManager(app)
        self.storage_media_manager = storage_media.StorageMediaManager(app)
        self.storage_media_serializer = storage_media.StorageMediaSerializer(app)
        self.storage_media_deserializer = storage_media.StorageMediaDeserializer(app)
        self.hda_manager = hdas.HDAManager(app)
        self.dataset_manager = datasets.DatasetManager(app)

    @expose_api
    def index(self, trans, **kwargs):
        """
        GET /api/storage_media: returns a list of installed storage media
        """
        user = self.user_manager.current_user(trans)
        if self.user_manager.is_anonymous(user):
            # an anonymous user is not expected to have installed a storage media.
            return []
        rtv = []
        for pm in user.storage_media:
            rtv.append(self.storage_media_serializer.serialize_to_view(
                pm, user=trans.user, trans=trans, **self._parse_serialization_params(kwargs, "summary")))
        return rtv

    @expose_api
    def show(self, trans, encoded_media_id, **kwargs):
        user = self.user_manager.current_user(trans)
        decoded_id = self.decode_id(encoded_media_id)

        try:
            media = next(x for x in user.storage_media if x.id == decoded_id)
        except StopIteration:
            raise exceptions.ObjectNotFound("User does not have StorageMedia with the given ID.")

        return self.storage_media_serializer.serialize_to_view(
            media,
            user=trans.user,
            trans=trans,
            **self._parse_serialization_params(kwargs, "detailed"))

    @expose_api
    def plug(self, trans, payload, **kwargs):
        """
        plug(self, trans, payload, **kwd)
        * POST /api/storage_media:
            Creates a new storage media.

        :type  trans: galaxy.web.framework.webapp.GalaxyWebTransaction
        :param trans: Galaxy web transaction.

        :type  payload: dict
        :param payload: A dictionary structure containing the following keys:
            - category: is the type of this storage media, its value is a key from `categories` bunch defined in the
            `StorageMedia` class.
            - path: a path in the storage media to be used (e.g., AWS S3 Bucket name).
            - usage (Optional): Sets the size of data persisted by Galaxy in this storage media.
        :rtype: dict
        :return: The newly created storage media.
        """
        if not isinstance(payload, dict):
            trans.response.status = 400
            return "Invalid payload data type. The payload is expected to be a dictionary," \
                   " but received data of type '%s'." % str(type(payload))

        missing_arguments = []
        category = payload.get("category")
        if category is None:
            missing_arguments.append("category")
        path = payload.get("path")
        if path is None:
            missing_arguments.append("path")
        if len(missing_arguments) > 0:
            trans.response.status = 400
            return "The following required arguments are missing in the payload: %s" % missing_arguments
        purgeable = string_as_bool(payload.get("purgeable", True))

        try:
            usage = float(payload.get("usage", "0.0"))
        except ValueError:
            return "Expected a floating-point number for the `usage` attribute, but received `{}`.".format(payload.get("usage"))

        if category != trans.app.model.StorageMedia.categories.LOCAL:
            raise exceptions.RequestParameterInvalidException(
                "Invalid category; received `{}`, expected either of the following categories {}.".format(
                    category,
                    [trans.app.model.StorageMedia.categories.AWS]))

        try:
            new_storage_media = self.storage_media_manager.create(
                user_id=trans.user.id,
                category=category,
                path=path,
                usage=usage,
                purgeable=purgeable,
                cache_size=trans.app.config.default_storage_media_cache_size)
            encoded_id = trans.app.security.encode_id(new_storage_media.id)
            new_storage_media.jobs_directory = os.path.join(
                trans.app.config.default_storage_media_jobs_directory,
                encoded_id)
            new_storage_media.cache_path = os.path.join(
                trans.app.config.default_storage_media_cache_path,
                encoded_id)
            self.storage_media_manager.session().flush()
            view = self.storage_media_serializer.serialize_to_view(
                new_storage_media, user=trans.user, trans=trans, **self._parse_serialization_params(kwargs, "summary"))
            # Do not use integer response codes (e.g., 200), as they are not accepted by the
            # 'wsgi_status' function in lib/galaxy/web/framework/base.py
            trans.response.status = '200 OK'
            log.debug('Created a new storage media of type `%s` for the user id `%s` ', category, str(trans.user.id))
            return view
        except ValueError as e:
            log.debug('An error occurred while creating a storage media. ' + str(e))
            trans.response.status = '400 Bad Request'
        except Exception as e:
            log.exception('An unexpected error has occurred while responding to the '
                          'create request of the storage media API. ' + str(e))
            # Do not use integer response code (see above).
            trans.response.status = '500 Internal Server Error'
        return []

    @expose_api
    def unplug(self, trans, encoded_media_id, **kwargs):
        """
        unplug(self, trans, id, **kwd)
        * DELETE /api/storage_media/{id}
            Deletes the storage media with the given ID, also deletes all the associated datasets and HDAs.

        :type  trans: galaxy.web.framework.webapp.GalaxyWebTransaction
        :param trans: Galaxy web transaction.

        :type id: string
        :param id: The encoded ID of the storage media to be deleted.

        :type kwd: dict
        :param kwd: (optional) dictionary structure containing extra parameters (e.g., `purge`).

        :rtype: dict
        :return: The deleted or purged storage media.
        """
        try:
            decoded_id = self.decode_id(encoded_media_id)
            media_to_delete = trans.sa_session.query(trans.app.model.StorageMedia).get(decoded_id)
            payload = kwargs.get('payload', None)
            purge = False if payload is None else string_as_bool(payload.get('purge', False))
            if purge:
                self.storage_media_manager.purge(media_to_delete)
            else:
                self.storage_media_manager.delete(media_to_delete)
            return self.storage_media_serializer.serialize_to_view(
                media_to_delete, user=trans.user, trans=trans, **self._parse_serialization_params(kwargs, "summary"))
        except exceptions.ObjectNotFound:
            trans.response.status = '404 Not Found'
            msg = 'The storage media with ID `{}` does not exist.'.format(str(encoded_media_id))
            log.debug(msg)
        except exceptions.ConfigDoesNotAllowException as e:
            trans.response.status = '403 Forbidden'
            msg = str(e)
            log.debug(msg)
        except AttributeError as e:
            trans.response.status = '500 Internal Server Error'
            msg = 'An unexpected error has occurred while deleting/purging a storage media in response to the ' \
                  'related API call. Maybe an inappropriate database manipulation. ' + str(e)
            log.error(msg)
        except Exception as e:
            trans.response.status = '500 Internal Server Error'
            msg = 'An unexpected error has occurred while deleting/purging a storage media in response to the ' \
                  'related API call. ' + str(e)
            log.error(msg)
        return msg

    @expose_api
    def update(self, trans, encoded_media_id, payload, **kwargs):
        msg_template = "Rejected user `" + str(trans.user.id) + "`'s request to update storage media config because of {}."

        decoded_id = self.decode_id(encoded_media_id)

        try:
            media_to_update = trans.sa_session.query(trans.app.model.StorageMedia).get(decoded_id)
            self.storage_media_deserializer.deserialize(media_to_update, payload, trans=trans, view="summary")
            return self.storage_media_serializer.serialize_to_view(media_to_update, trans=trans, view="summary")
        except exceptions.MalformedId as e:
            raise e
        except Exception as e:
            log.exception(msg_template.format("exception while updating the StorageMedia record with "
                                              "ID: `{}`.".format(decoded_id)))
            raise exceptions.InternalServerError('An unexpected error has occurred while responding '
                                                 'to the PUT request of the StorageMedia API.' + unicodify(e))
