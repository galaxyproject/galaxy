"""
API operations on Cloud-based storages, such as Amazon Simple Storage Service (S3).
"""

import logging

from galaxy import exceptions
from galaxy.exceptions import ActionInputError
from galaxy.managers import (
    cloud,
    datasets
)
from galaxy.web import _future_expose_api as expose_api
from galaxy.web.base.controller import BaseAPIController

log = logging.getLogger(__name__)


class CloudController(BaseAPIController):
    """
    RESTfull controller for interaction with Amazon S3.
    """

    def __init__(self, app):
        super(CloudController, self).__init__(app)
        self.cloud_manager = cloud.CloudManager(app)
        self.datasets_serializer = datasets.DatasetSerializer(app)

    @expose_api
    def index(self, trans, **kwargs):
        """
        * GET /api/cloud/storage
            Lists cloud-based buckets (e.g., S3 bucket, Azure blob) user has defined.
        :param trans:
        :param kwargs:
        :return: A list of cloud-based buckets user has defined.
        """
        # TODO: This can be implemented leveraging PluggedMedia objects (part of the user-based object store project)
        trans.response.status = 501
        return 'Not Implemented'

    @expose_api
    def upload(self, trans, payload, **kwargs):
        """
        * POST /api/cloud/storage/upload
            Uploads given objects from a given cloud-based bucket to a Galaxy history.
        :type  trans: galaxy.web.framework.webapp.GalaxyWebTransaction
        :param trans: Galaxy web transaction

        :type  payload: dict
        :param payload: A dictionary structure containing the following keys:
            *   history_id:    the (encoded) id of history to which the object should be uploaded to.
            *   bucket:        the name of a bucket from which data should be uploaded from (e.g., a bucket name on AWS S3).
            *   objects:       a list of the names of objects to be uploaded.
            *   credentials:   a dictionary containing all the credentials required to authenticated to the
            specified provider (e.g., {"secret_key": YOUR_AWS_SECRET_TOKEN, "access_key": YOUR_AWS_ACCESS_TOKEN}).
            *   input_args     [Optional; default value is an empty dict] a dictionary containing the following keys:

                                **   `dbkey`:           [Optional; default value: is `?`]
                                                        Sets the genome (e.g., `hg19`) of the objects being
                                                        uploaded to Galaxy.

                                **   `file_type`:       [Optional; default value is `auto`]
                                                        Sets the Galaxy datatype (e.g., `bam`) for the
                                                        objects being uploaded to Galaxy. See the following
                                                        link for a complete list of Galaxy data types:
                                                        https://galaxyproject.org/learn/datatypes/

                                **   `space_to_tab`:    [Optional; default value is `False`]
                                                        A boolean value ("true" or "false") that sets if spaces
                                                        should be converted to tab in the objects being
                                                        uploaded to Galaxy. Applicable only if `to_posix_lines`
                                                        is True

                                **   `to_posix_lines`:  [Optional; default value is `Yes`]
                                                        A boolean value ("true" or "false"); if "Yes", converts
                                                        universal line endings to POSIX line endings. Set to
                                                        "False" if you upload a gzip, bz2 or zip archive
                                                        containing a binary file.

        :param kwargs:

        :rtype:  dictionary
        :return: a dictionary containing a `summary` view of the datasets copied from the given cloud-based storage.
        """
        if not isinstance(payload, dict):
            raise ActionInputError('Invalid payload data type. The payload is expected to be a dictionary, '
                                   'but received data of type `{}`.'.format(str(type(payload))))

        missing_arguments = []
        encoded_history_id = payload.get("history_id", None)
        if encoded_history_id is None:
            missing_arguments.append("history_id")

        bucket = payload.get("bucket", None)
        if bucket is None:
            missing_arguments.append("bucket")

        objects = payload.get("objects", None)
        if objects is None:
            missing_arguments.append("objects")

        encoded_authz_id = payload.get("authz_id", None)
        if encoded_authz_id is None:
            missing_arguments.append("authz_id")

        if len(missing_arguments) > 0:
            raise ActionInputError("The following required arguments are missing in the payload: {}".format(missing_arguments))

        try:
            history_id = self.decode_id(encoded_history_id)
        except exceptions.MalformedId as e:
            raise ActionInputError('Invalid history ID. {}'.format(e))

        try:
            authz_id = self.decode_id(encoded_authz_id)
        except exceptions.MalformedId as e:
            raise ActionInputError('Invalid authz ID. {}'.format(e))

        if not isinstance(objects, list):
            raise ActionInputError('The `objects` should be a list, but received an object of type {} instead.'.format(
                type(objects)))

        datasets = self.cloud_manager.upload(trans=trans,
                                             history_id=history_id,
                                             bucket_name=bucket,
                                             objects=objects,
                                             authz_id=authz_id,
                                             input_args=payload.get("input_args", None))
        rtv = []
        for dataset in datasets:
            rtv.append(self.datasets_serializer.serialize_to_view(dataset, view='summary'))
        return rtv

    @expose_api
    def download(self, trans, payload, **kwargs):
        """
        * POST /api/cloud/storage/download
            Downloads given dataset(s) in a given history to a given cloud-based bucket. Each dataset is named
            using the label assigned to the dataset in the given history (see `HistoryDatasetAssociation.name`).
            If no dataset ID is given, this API downloads all the datasets belonging to a given history to a given
            cloud-based bucket.
        :type  trans: galaxy.web.framework.webapp.GalaxyWebTransaction
        :param trans: Galaxy web transaction

        :type  payload: dictionary
        :param payload: A dictionary structure containing the following keys:
            *   history_id              the (encoded) id of history from which the object should be downloaed.
            *   bucket:                 the name of a bucket to which data should be downloaded (e.g., a bucket name on AWS S3).
            *   authz_id:               the encoded ID of CloudAuthz to be used for authorizing access to the resource
                                        provider. You may get a list of the defined authorizations via
                                        `/api/cloud/authz`. Also, you can use `/api/cloud/authz/create` to define a
                                        new authorization.
            *   dataset_ids:            [Optional; default: None]
                                        A list of encoded dataset IDs belonging to the specified history
                                        that should be downloaded to the given bucket. If not provided, Galaxy downloads
                                        all the datasets belonging the specified history.
            *   overwrite_existing:     [Optional; default: False]
                                        A boolean value. If set to "True", and an object with same name of the dataset
                                        to be downloaded already exist in the bucket, Galaxy replaces the existing object
                                        with the dataset to be downloaded. If set to "False", Galaxy appends datetime
                                        to the dataset name to prevent overwriting an existing object.

        :param kwargs:

        :rtype:     dictionary
        :return:    Information about the downloaded datasets, containing the following keys:
                        *   `bucket_name`:          The name of bucket/container to which the listed datasets are downloaded.
                        *   `downloaded_dataset`:   A list of JSON objects describing the download datasets.
        """
        missing_arguments = []
        encoded_history_id = payload.get("history_id", None)
        if encoded_history_id is None:
            missing_arguments.append("history_id")

        bucket = payload.get("bucket", None)
        if bucket is None:
            missing_arguments.append("bucket")

        encoded_authz_id = payload.get("authz_id", None)
        if encoded_authz_id is None:
            missing_arguments.append("authz_id")

        if len(missing_arguments) > 0:
            raise ActionInputError("The following required arguments are missing in the payload: {}".format(missing_arguments))

        try:
            history_id = self.decode_id(encoded_history_id)
        except exceptions.MalformedId as e:
            raise ActionInputError('Invalid history ID. {}'.format(e))

        try:
            authz_id = self.decode_id(encoded_authz_id)
        except exceptions.MalformedId as e:
            raise ActionInputError('Invalid authz ID. {}'.format(e))

        encoded_dataset_ids = payload.get("dataset_ids", None)
        if encoded_dataset_ids is None:
            dataset_ids = None
        else:
            dataset_ids = set()
            invalid_dataset_ids = []
            for encoded_id in encoded_dataset_ids:
                try:
                    dataset_ids.add(self.decode_id(encoded_id))
                except exceptions.MalformedId:
                    invalid_dataset_ids.append(encoded_id)
            if len(invalid_dataset_ids) > 0:
                raise ActionInputError("The following provided dataset IDs are invalid, please correct them and retry. "
                                       "{}".format(invalid_dataset_ids))

        downloaded, failed = self.cloud_manager.download(trans=trans,
                                                         history_id=history_id,
                                                         bucket_name=bucket,
                                                         authz_id=authz_id,
                                                         dataset_ids=dataset_ids,
                                                         overwrite_existing=payload.get("overwrite_existing", False))
        return {'downloaded_dataset_labels': downloaded,
                'failed_dataset_labels': failed,
                'bucket_name': bucket}
