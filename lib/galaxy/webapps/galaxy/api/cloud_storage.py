"""
API operations on Cloud-based storages, such as Amazon Simple Storage Service (S3).
"""

import logging

from galaxy import web
from galaxy.web.base.controller import BaseAPIController
from galaxy.managers import cloud_storages

log = logging.getLogger(__name__)


class CloudStorageController(BaseAPIController):
    """
    RESTfull controller for interaction with Amazon S3.
    """

    def __init__(self, app):
        super(CloudStorageController, self).__init__(app)

    @web.expose_api
    def index(self, trans, **kwargs):
        """
        * GET /api/cloud_storage
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
        * POST /api/cloud_storage/download
            Downloads a given object from a given cloud-based container.
        :type  trans: galaxy.web.framework.webapp.GalaxyWebTransaction
        :param trans: Galaxy web transaction

        :type  payload: dict
        :param payload: A dictionary structure containing the following keys:


        :param kwargs:

        :rtype:  boolean
        :return: True/False if the given object is successfully downloaded from the cloud-based storage.
        """
        pass

    @web.expose_api
    def upload(self, trans, payload, **kwargs):
        """
        * POST /api/cloud_storage/upload
            Uploads a given dataset to a given cloud-based container.
        :param trans:
        :param payload:
        :param kwargs:
        :return:
        """
        pass