"""
Manager and Serializer for storage media.
"""

import logging

from galaxy import exceptions
from galaxy import model
from galaxy.managers import (
    base,
    datasets,
    deletable,
    hdas,
    sharable
)

log = logging.getLogger(__name__)


class StorageMediaManager(base.ModelManager, deletable.PurgableManagerMixin):

    model_class = model.StorageMedia
    foreign_key_name = "storage_media"

    def __init__(self, app, *args, **kwargs):
        super(StorageMediaManager, self).__init__(app, *args, **kwargs)
        self.hda_manager = hdas.HDAManager(app)
        self.dataset_manager = datasets.DatasetManager(app)

    def delete(self, storage_media, **kwargs):
        """
        Deletes the given storage media by taking the following steps:
        (1) marks the storage media `deleted` in the database (i.e., setting
        the `deleted` attribute to True);
        (2) marks `deleted` all the datasets persisted on the storage media;
        (3) marks `deleted` all the StorageMedia-Dataset associations.
        :param storage_media: The storage media to be deleted.
        :type storage_media: galaxy.model.StorageMedia
        :return: returns the deleted storage media.
        """
        super(StorageMediaManager, self).delete(storage_media, kwargs)
        for assoc in storage_media.data_association:
            self.hda_manager.delete(assoc, kwargs)
            self.dataset_manager.delete(assoc.dataset, kwargs)
            super(StorageMediaManager, self).delete(assoc, kwargs)
        self.session().flush()
        return storage_media

    def undelete(self, storage_media, **kwargs):
        """
        Un-deletes the given storage media by taking the following steps:
        (1) marks the storage media `un-deleted` in the database (i.e., setting
        the `deleted` attribute to False);
        (2) marks `un-deleted` all the datasets persisted on the storage media;
        (3) marks `un-deleted` all the StorageMedia-Dataset associations.
        :param storage_media: The storage media to be deleted.
        :type storage_media: galaxy.model.StorageMedia
        :return: returns the deleted storage media.
        """
        super(StorageMediaManager, self).undelete(storage_media, kwargs)
        for assoc in storage_media.data_association:
            self.hda_manager.delete(assoc, kwargs)
            self.dataset_manager.delete(assoc.dataset, kwargs)
            super(StorageMediaManager, self).undelete(assoc, kwargs)
        self.session().flush()
        return storage_media

    def purge(self, storage_media, **kwargs):
        """
        Purges a storage media by taking the following steps:
        (1) marks the storage media `purged` in the database;
        (2) deletes all the datasets persisted on the storage media;
        (3) marks all the HDAs associated with the deleted datasets as purged.
        This operation does NOT `delete` the storage media physically
        (e.g., it does not delete a S3 bucket), because the storage media
        (e.g., a S3 bucket) may contain data other than those loaded
        or mounted on Galaxy which deleting the media (e.g., deleting
        a S3 bucket) will result in unexpected file deletes.
        :param storage_media: The media to be purged.
        :type: storage_media: galaxy.model.StorageMedia
        :return: returns the purged storage media.
        """
        if not storage_media.is_purgeable():
            raise exceptions.ConfigDoesNotAllowException(
                "The storage media (ID: `{}`; category: `{}`) is not purgeable; because {}".format(
                    storage_media.id, storage_media.category,
                    "it`s purgeable attribute is set to `False`." if storage_media.purgeable is False
                    else "it contains at least one dataset which is not purgeable."))
        for i, assoc in enumerate(storage_media.data_association):
            for hda in assoc.dataset.history_associations:
                self.hda_manager.purge(hda)
            self.dataset_manager.purge(assoc.dataset, storage_media=storage_media)
            storage_media.data_association[i].purged = True
        storage_media.purged = True
        self.session().flush()
        return storage_media


class StorageMediaSerializer(base.ModelSerializer, deletable.PurgableSerializerMixin):
    """
    Interface/service object for serializing storage media into dictionaries.
    """
    model_manager_class = StorageMediaManager

    def __init__(self, app, **kwargs):
        super(StorageMediaSerializer, self).__init__(app, **kwargs)
        self.storage_media_manager = self.manager

        self.default_view = "summary"
        self.add_view("summary", [
            "id",
            "model_class",
            "user_id",
            "usage",
            "category",
            "path"
        ])
        self.add_view("detailed", [
            "id",
            "model_class",
            "user_id",
            "create_time",
            "update_time",
            "usage",
            "category",
            "path",
            "deleted",
            "purged",
            "purgeable"
        ])

    def add_serializers(self):
        super(StorageMediaSerializer, self).add_serializers()
        deletable.PurgableSerializerMixin.add_serializers(self)

        # Arguments of the following lambda functions:
        # i  : an instance of galaxy.model.StorageMedia.
        # k  : serialized dictionary key (e.g., "model_class", "category", and "path").
        # **c: a dictionary containing "trans" and "user" objects.
        self.serializers.update({
            "id"         : lambda i, k, **c: self.app.security.encode_id(i.id),
            "model_class": lambda *a, **c: "StorageMedia",
            "user_id"    : lambda i, k, **c: self.app.security.encode_id(i.user_id),
            "usage"      : lambda i, k, **c: str(i.usage),
            "category"   : lambda i, k, **c: i.category,
            "path"       : lambda i, k, **c: i.path,
            "deleted"    : lambda i, k, **c: i.deleted,
            "purged"     : lambda i, k, **c: i.purged,
            "purgeable"  : lambda i, k, **c: i.purgeable
        })


class StorageMediaDeserializer(sharable.SharableModelDeserializer, deletable.PurgableDeserializerMixin):

    model_manager_class = StorageMediaManager

    def add_deserializers(self):
        super(StorageMediaDeserializer, self).add_deserializers()
        self.deserializers.update({
            "path": self.default_deserializer
        })
