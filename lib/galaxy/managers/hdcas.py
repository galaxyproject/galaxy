"""
Manager and Serializer for HDCAs.

HistoryDatasetCollectionAssociations (HDCAs) are datasets contained or created in a
history.
"""
import logging

from galaxy import model
from galaxy.managers import (
    annotatable,
    base,
    deletable,
    hdas,
    secured,
    taggable
)

log = logging.getLogger(__name__)


# TODO: to DatasetCollectionInstanceManager
class HDCAManager(
        base.ModelManager,
        secured.AccessibleManagerMixin,
        secured.OwnableManagerMixin,
        deletable.PurgableManagerMixin,
        taggable.TaggableManagerMixin,
        annotatable.AnnotatableManagerMixin):
    """
    Interface/service object for interacting with HDCAs.
    """
    model_class = model.HistoryDatasetCollectionAssociation
    foreign_key_name = 'history_dataset_collection_association'

    tag_assoc = model.HistoryDatasetCollectionTagAssociation
    annotation_assoc = model.HistoryDatasetCollectionAssociationAnnotationAssociation

    def __init__(self, app):
        """
        Set up and initialize other managers needed by hdcas.
        """
        super(HDCAManager, self).__init__(app)

    def map_datasets(self, content, fn, *parents):
        """
        Iterate over the datasets of a given collection, recursing into collections, and
        calling fn on each dataset.

        Uses the same kwargs as `contents` above.
        """
        returned = []
        # lots of nesting going on within the nesting
        collection = content.collection if hasattr(content, 'collection') else content
        this_parents = (content, ) + parents
        for element in collection.elements:
            next_parents = (element, ) + this_parents
            if element.is_collection:
                processed_list = self.map_datasets(element.child_collection, fn, *next_parents)
                returned.extend(processed_list)
            else:
                processed = fn(element.dataset_instance, *next_parents)
                returned.append(processed)
        return returned

    # TODO: un-stub


# serializers
# -----------------------------------------------------------------------------
class DCESerializer(base.ModelSerializer):
    """
    Serializer for DatasetCollectionElements.
    """

    def __init__(self, app):
        super(DCESerializer, self).__init__(app)
        self.hda_serializer = hdas.HDASerializer(app)
        self.dc_serializer = DCSerializer(app, dce_serializer=self)

        self.default_view = 'summary'
        self.add_view('summary', [
            'id', 'model_class',
            'element_index',
            'element_identifier',
            'element_type',
            'object'
        ])

    def add_serializers(self):
        super(DCESerializer, self).add_serializers()
        self.serializers.update({
            'model_class'   : lambda *a, **c: 'DatasetCollectionElement',
            'object'        : self.serialize_object
        })

    def serialize_object(self, item, key, **context):
        if item.hda:
            return self.hda_serializer.serialize_to_view(item.hda, view='summary', **context)
        if item.child_collection:
            return self.dc_serializer.serialize_to_view(item.child_collection, view='detailed', **context)
        return 'object'


class DCSerializer(base.ModelSerializer):
    """
    Serializer for DatasetCollections.
    """

    def __init__(self, app, dce_serializer=None):
        super(DCSerializer, self).__init__(app)
        self.dce_serializer = dce_serializer or DCESerializer(app)

        self.default_view = 'summary'
        self.add_view('summary', [
            'id',
            'create_time',
            'update_time',
            'collection_type',
            'populated_state',
            'populated_state_message',
            'element_count',
        ])
        self.add_view('detailed', [
            'populated',
            'elements',
        ], include_keys_from='summary')

    def add_serializers(self):
        super(DCSerializer, self).add_serializers()
        self.serializers.update({
            'model_class'   : lambda *a, **c: 'DatasetCollection',
            'elements'      : self.serialize_elements,
        })

    def serialize_elements(self, item, key, **context):
        returned = []
        for element in item.elements:
            serialized = self.dce_serializer.serialize_to_view(element, view='summary', **context)
            returned.append(serialized)
        return returned


class DCASerializer(base.ModelSerializer):
    """
    Base (abstract) Serializer class for HDCAs and LDCAs.
    """

    def __init__(self, app, dce_serializer=None):
        super(DCASerializer, self).__init__(app)
        self.dce_serializer = dce_serializer or DCESerializer(app)

        self.default_view = 'summary'
        self.add_view('summary', [
            'id',
            'create_time', 'update_time',
            'collection_type',
            'populated_state',
            'populated_state_message',
            'element_count',
        ])
        self.add_view('detailed', [
            'populated',
            'elements',
        ], include_keys_from='summary')

    def add_serializers(self):
        super(DCASerializer, self).add_serializers()
        # most attributes are (kinda) proxied from DCs - we need a serializer to proxy to
        self.dc_serializer = DCSerializer(self.app)
        # then set the serializers to point to it for those attrs
        collection_keys = [
            'create_time',
            'update_time',
            'collection_type',
            'populated',
            'populated_state',
            'populated_state_message',
            'elements',
            'element_count',
        ]
        for key in collection_keys:
            self.serializers[key] = self._proxy_to_dataset_collection(key=key)

    def _proxy_to_dataset_collection(self, serializer=None, key=None):
        # dataset_collection associations are (rough) proxies to datasets - access their serializer using this remapping fn
        # remapping done by either kwarg key: IOW dataset attr key (e.g. populated_state)
        # or by kwarg serializer: a function that's passed in (e.g. elements)
        if key:
            return lambda i, k, **c: self.dc_serializer.serialize(i.collection, [k], **c)[k]
        if serializer:
            return lambda i, k, **c: serializer(i.collection, key or k, **c)
        raise TypeError('kwarg serializer or key needed')


class HDCASerializer(
        DCASerializer,
        taggable.TaggableSerializerMixin,
        annotatable.AnnotatableSerializerMixin):
    """
    Serializer for HistoryDatasetCollectionAssociations.
    """

    def __init__(self, app):
        super(HDCASerializer, self).__init__(app)
        self.hdca_manager = HDCAManager(app)

        self.default_view = 'summary'
        self.add_view('summary', [
            'id',
            'type_id',
            'name',
            'history_id', 'hid',
            'history_content_type',

            'collection_type',
            'populated_state',
            'populated_state_message',
            'element_count',

            'job_source_id',
            'job_source_type',

            'name',
            'type_id',
            'deleted',
            # 'purged',
            'visible',
            'type', 'url',
            'create_time', 'update_time',
            'tags',  # TODO: detail view only (maybe)
        ])
        self.add_view('detailed', [
            'populated',
            'elements'
        ], include_keys_from='summary')

    def add_serializers(self):
        super(HDCASerializer, self).add_serializers()
        taggable.TaggableSerializerMixin.add_serializers(self)
        annotatable.AnnotatableSerializerMixin.add_serializers(self)

        self.serializers.update({
            'model_class'               : lambda *a, **c: self.hdca_manager.model_class.__class__.__name__,
            # TODO: remove
            'type'                      : lambda *a, **c: 'collection',
            # part of a history and container
            'history_id'                : self.serialize_id,
            'history_content_type'      : lambda *a, **c: self.hdca_manager.model_class.content_type,
            'type_id'                   : self.serialize_type_id,
            'job_source_id'             : self.serialize_id,

            'url'   : lambda i, k, **c: self.url_for('history_content_typed',
                                                     history_id=self.app.security.encode_id(i.history_id),
                                                     id=self.app.security.encode_id(i.id),
                                                     type=self.hdca_manager.model_class.content_type),
        })
