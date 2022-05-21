"""
Manager and Serializer for HDCAs.

HistoryDatasetCollectionAssociations (HDCAs) are datasets contained or created in a
history.
"""
import logging
from typing import Dict

from galaxy import model
from galaxy.managers import (
    annotatable,
    base,
    deletable,
    hdas,
    secured,
    taggable,
)
from galaxy.managers.collections_util import get_hda_and_element_identifiers
from galaxy.model.tags import GalaxyTagHandler
from galaxy.structured_app import (
    MinimalManagerApp,
    StructuredApp,
)
from galaxy.util.zipstream import ZipstreamWrapper

log = logging.getLogger(__name__)


def stream_dataset_collection(dataset_collection_instance, upstream_mod_zip=False, upstream_gzip=False):
    archive_name = f"{dataset_collection_instance.hid}: {dataset_collection_instance.name}"
    archive = ZipstreamWrapper(
        archive_name=archive_name,
        upstream_mod_zip=upstream_mod_zip,
        upstream_gzip=upstream_gzip,
    )
    write_dataset_collection(dataset_collection_instance, archive)
    return archive


def write_dataset_collection(dataset_collection_instance, archive):
    names, hdas = get_hda_and_element_identifiers(dataset_collection_instance)
    for name, hda in zip(names, hdas):
        if hda.state != hda.states.OK:
            continue
        for file_path, relpath in hda.datatype.to_archive(dataset=hda, name=name):
            archive.write(file_path, relpath)
    return archive


def set_collection_attributes(dataset_element, *payload):
    for attribute, value in payload:
        setattr(dataset_element, attribute[1], value[1])


# TODO: to DatasetCollectionInstanceManager
class HDCAManager(
    base.ModelManager,
    secured.AccessibleManagerMixin,
    secured.OwnableManagerMixin,
    deletable.PurgableManagerMixin,
    taggable.TaggableManagerMixin,
    annotatable.AnnotatableManagerMixin,
):
    """
    Interface/service object for interacting with HDCAs.
    """

    model_class = model.HistoryDatasetCollectionAssociation
    foreign_key_name = "history_dataset_collection_association"

    tag_assoc = model.HistoryDatasetCollectionTagAssociation
    annotation_assoc = model.HistoryDatasetCollectionAssociationAnnotationAssociation

    def __init__(self, app: MinimalManagerApp):
        """
        Set up and initialize other managers needed by hdas.
        """
        super().__init__(app)
        self.tag_handler = app[GalaxyTagHandler]

    def map_datasets(self, content, fn, *parents):
        """
        Iterate over the datasets of a given collection, recursing into collections, and
        calling fn on each dataset.

        Uses the same kwargs as `contents` above.
        """
        returned = []
        # lots of nesting going on within the nesting
        collection = content.collection if hasattr(content, "collection") else content
        this_parents = (content,) + parents
        for element in collection.elements:
            next_parents = (element,) + this_parents
            if element.is_collection:
                processed_list = self.map_datasets(element.child_collection, fn, *next_parents)
                returned.extend(processed_list)
            else:
                processed = fn(element.dataset_instance, *next_parents)
                returned.append(processed)
        return returned

    def update_attributes(self, content, payload: Dict):
        # pre-requisite checked that attributes are valid
        self.map_datasets(content, fn=lambda item, *args: set_collection_attributes(item, payload.items()))


# serializers
# -----------------------------------------------------------------------------
class DCESerializer(base.ModelSerializer):
    """
    Serializer for DatasetCollectionElements.
    """

    def __init__(self, app: StructuredApp):
        super().__init__(app)
        self.hda_serializer = hdas.HDASerializer(app)
        self.dc_serializer = DCSerializer(app, dce_serializer=self)

        self.default_view = "summary"
        self.add_view("summary", ["id", "model_class", "element_index", "element_identifier", "element_type", "object"])

    def add_serializers(self):
        super().add_serializers()
        self.serializers.update(
            {"model_class": lambda *a, **c: "DatasetCollectionElement", "object": self.serialize_object}
        )

    def serialize_object(self, item, key, **context):
        if item.hda:
            return self.hda_serializer.serialize_to_view(item.hda, view="summary", **context)
        if item.child_collection:
            return self.dc_serializer.serialize_to_view(item.child_collection, view="detailed", **context)
        return "object"


class DCSerializer(base.ModelSerializer):
    """
    Serializer for DatasetCollections.
    """

    def __init__(self, app: StructuredApp, dce_serializer=None):
        super().__init__(app)
        self.dce_serializer = dce_serializer or DCESerializer(app)

        self.default_view = "summary"
        self.add_view(
            "summary",
            [
                "id",
                "create_time",
                "update_time",
                "collection_type",
                "populated_state",
                "populated_state_message",
                "element_count",
            ],
        )
        self.add_view(
            "detailed",
            [
                "populated",
                "elements",
            ],
            include_keys_from="summary",
        )

    def add_serializers(self):
        super().add_serializers()
        self.serializers.update(
            {
                "model_class": lambda *a, **c: "DatasetCollection",
                "elements": self.serialize_elements,
            }
        )

    def serialize_elements(self, item, key, **context):
        returned = []
        for element in item.elements:
            serialized = self.dce_serializer.serialize_to_view(element, view="summary", **context)
            returned.append(serialized)
        return returned


class DCASerializer(base.ModelSerializer):
    """
    Base (abstract) Serializer class for HDCAs and LDCAs.
    """

    app: StructuredApp

    def __init__(self, app: StructuredApp, dce_serializer=None):
        super().__init__(app)
        self.dce_serializer = dce_serializer or DCESerializer(app)

        self.default_view = "summary"
        self.add_view(
            "summary",
            [
                "id",
                "create_time",
                "update_time",
                "collection_type",
                "populated_state",
                "populated_state_message",
                "element_count",
            ],
        )
        self.add_view(
            "detailed",
            [
                "populated",
                "elements",
            ],
            include_keys_from="summary",
        )

    def add_serializers(self):
        super().add_serializers()
        # most attributes are (kinda) proxied from DCs - we need a serializer to proxy to
        self.dc_serializer = DCSerializer(self.app)
        # then set the serializers to point to it for those attrs
        collection_keys = [
            "create_time",
            "update_time",
            "collection_type",
            "populated",
            "populated_state",
            "populated_state_message",
            "elements",
            "element_count",
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
        raise TypeError("kwarg serializer or key needed")


class HDCASerializer(DCASerializer, taggable.TaggableSerializerMixin, annotatable.AnnotatableSerializerMixin):
    """
    Serializer for HistoryDatasetCollectionAssociations.
    """

    def __init__(self, app: StructuredApp):
        super().__init__(app)
        self.hdca_manager = HDCAManager(app)

        self.default_view = "summary"
        self.add_view(
            "summary",
            [
                "id",
                "type_id",
                "name",
                "history_id",
                "collection_id",
                "hid",
                "history_content_type",
                "collection_type",
                "populated_state",
                "populated_state_message",
                "element_count",
                "job_source_id",
                "job_source_type",
                "job_state_summary",
                "name",
                "type_id",
                "deleted",
                "visible",
                "type",
                "url",
                "create_time",
                "update_time",
                "tags",
                "contents_url",
            ],
        )
        self.add_view(
            "detailed",
            [
                "populated",
                "elements",
                "elements_datatypes",
            ],
            include_keys_from="summary",
        )

    def add_serializers(self):
        super().add_serializers()
        taggable.TaggableSerializerMixin.add_serializers(self)
        annotatable.AnnotatableSerializerMixin.add_serializers(self)
        serializers: Dict[str, base.Serializer] = {
            "model_class": lambda item, key, **context: self.hdca_manager.model_class.__class__.__name__,
            # TODO: remove
            "type": lambda item, key, **context: "collection",
            # part of a history and container
            "history_id": self.serialize_id,
            "history_content_type": lambda item, key, **context: self.hdca_manager.model_class.content_type,
            "type_id": self.serialize_type_id,
            "job_source_id": self.serialize_id,
            "url": lambda item, key, **context: self.url_for(
                "history_content_typed",
                history_id=self.app.security.encode_id(item.history_id),
                id=self.app.security.encode_id(item.id),
                type=self.hdca_manager.model_class.content_type,
            ),
            "contents_url": self.generate_contents_url,
            "job_state_summary": self.serialize_job_state_summary,
            "elements_datatypes": self.serialize_elements_datatypes,
        }
        self.serializers.update(serializers)

    def generate_contents_url(self, item, key, **context):
        encode_id = self.app.security.encode_id
        trans = context.get("trans")
        url_for = trans.url_builder if trans and trans.url_builder else self.url_for
        contents_url = url_for(
            "contents_dataset_collection", hdca_id=encode_id(item.id), parent_id=encode_id(item.collection_id)
        )
        return contents_url

    def serialize_job_state_summary(self, item, key, **context):
        return item.job_state_summary_dict

    def serialize_elements_datatypes(self, item, key, **context):
        extensions_set = item.dataset_dbkeys_and_extensions_summary[1]
        return list(extensions_set)
