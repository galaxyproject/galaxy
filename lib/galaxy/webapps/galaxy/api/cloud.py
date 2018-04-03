"""
API operations on Cloud-based storages, such as Amazon Simple Storage Service (S3).
"""

import logging

from galaxy import exceptions
from galaxy import web
from galaxy.managers import cloud
from galaxy.web.base.controller import BaseAPIController

log = logging.getLogger(__name__)


class CloudController(BaseAPIController):
    """
    RESTfull controller for interaction with Amazon S3.
    """

    def __init__(self, app):
        super(CloudController, self).__init__(app)
        self.cloud_manager = cloud.CloudManager(app)

    @web.expose_api
    def index(self, trans, **kwargs):
        """
        * GET /api/cloud
            Lists cloud-based containers (e.g., S3 bucket, Azure blob) user has defined.
        :param trans:
        :param kwargs:
        :return: A list of cloud-based containers user has defined.
        """
        # TODO: This can be implemented leveraging PluggedMedia objects (part of the user-based object store project)
        trans.response.status = 501
        return 'Not Implemented'

    @web.expose_api
    def download(self, trans, payload, **kwargs):
        """
        * POST /api/cloud/download
            Downloads a given object from a given cloud-based container.
        :type  trans: galaxy.web.framework.webapp.GalaxyWebTransaction
        :param trans: Galaxy web transaction

        :type  payload: dict
        :param payload: A dictionary structure containing the following keys:
            *   history_id:    the (encoded) id of history to which the object should be downloaded to.
            *   provider:      the name of cloud-based resource provided (e.g., 'aws' or 'azure').
            *   container:     is the name of container from which data should be downloaded (e.g., a bucket name on AWS S3).
            *   object:        is the name of an object to be downloaded.
            *   credentials:   is a dictionary containing all the credentials required to authenticated to the
            specified provider (e.g., {"secret_key": YOUR_AWS_SECRET_TOKEN, "access_key": YOUR_AWS_ACCESS_TOKEN}).

        :param kwargs:

        :rtype:  dictionary
        :return: a dictionary with the following keys:
            *   status:     HTTP status code (e.g., "200" if the provided object is successfully downloaded to Galaxy).
            *   message:    a description complementary to the status code.
        """
        if not isinstance(payload, dict):
            trans.response.status = "400"
            return {'status': "400",
                    'message': 'Invalid payload data type. The payload is expected to be a dictionary, '
                               'but received data of type `%s`.' % str(type(payload))}

        missing_arguments = []
        encoded_history_id = payload.get("history_id", None)
        if encoded_history_id is None:
            missing_arguments.append("history_id")

        provider = payload.get("provider", None)
        if provider is None:
            missing_arguments.append("provider")

        container = payload.get("container", None)
        if container is None:
            missing_arguments.append("container")

        obj = payload.get("object", None)
        if obj is None:
            missing_arguments.append("object")

        credentials = payload.get("credentials", None)
        if credentials is None:
            missing_arguments.append("credentials")

        if len(missing_arguments) > 0:
            trans.response.status = "400"
            return {'status': "400",
                    'message': "The following required arguments are missing in the payload: %s" % missing_arguments}

        try:
            history_id = self.decode_id(encoded_history_id)
        except exceptions.MalformedId as e:
            trans.response.status = "400"
            return {'status': "400", 'message': 'Invalid history ID. {}'.format(e)}

        status, message = self.cloud_manager.download(trans=trans,
                                                      history_id=history_id,
                                                      provider=provider,
                                                      container=container,
                                                      obj=obj,
                                                      credentials=credentials)
        trans.response.status = status
        return {'status': status, 'message': message}

    @web.expose_api
    def upload(self, trans, payload, **kwargs):
        """
        * POST /api/cloud/upload
            Uploads a given dataset to a given cloud-based container.
        :param trans:
        :param payload:
        :param kwargs:
        :return:
        """
        trans.response.status = 501
        return 'Not Implemented'
