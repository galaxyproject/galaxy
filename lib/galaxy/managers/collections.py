import logging
from typing import (
    Any,
    Dict,
    List,
    Union,
)
from zipfile import ZipFile

from sqlalchemy.orm import (
    joinedload,
    Query,
)

from galaxy import model
from galaxy.datatypes.registry import Registry
from galaxy.exceptions import (
    ItemAccessibilityException,
    MessageException,
    RequestParameterInvalidException,
)
from galaxy.managers.collections_util import validate_input_element_identifiers
from galaxy.model.dataset_collections import builder
from galaxy.model.dataset_collections.matching import MatchingCollections
from galaxy.model.dataset_collections.registry import DATASET_COLLECTION_TYPES_REGISTRY
from galaxy.model.dataset_collections.type_description import COLLECTION_TYPE_DESCRIPTION_FACTORY
from galaxy.model.mapping import GalaxyModelMapping
from galaxy.model.tags import GalaxyTagHandler
from galaxy.schema.tasks import PrepareDatasetCollectionDownload
from galaxy.security.idencoding import IdEncodingHelper
from galaxy.util import validation
from galaxy.web.short_term_storage import (
    ShortTermStorageMonitor,
    storage_context,
)
from .hdas import (
    HDAManager,
    HistoryDatasetAssociationNoHistoryException,
)
from .hdcas import write_dataset_collection
from .histories import HistoryManager
from .lddas import LDDAManager

log = logging.getLogger(__name__)

ERROR_INVALID_ELEMENTS_SPECIFICATION = "Create called with invalid parameters, must specify element identifiers."
ERROR_NO_COLLECTION_TYPE = "Create called without specifying a collection type."


class DatasetCollectionManager:
    """
    Abstraction for interfacing with dataset collections instance - ideally abstracts
    out model and plugin details.
    """

    ELEMENTS_UNINITIALIZED = object()

    def __init__(
        self,
        model: GalaxyModelMapping,
        security: IdEncodingHelper,
        hda_manager: HDAManager,
        history_manager: HistoryManager,
        tag_handler: GalaxyTagHandler,
        ldda_manager: LDDAManager,
        short_term_storage_monitor: ShortTermStorageMonitor,
    ):
        self.type_registry = DATASET_COLLECTION_TYPES_REGISTRY
        self.collection_type_descriptions = COLLECTION_TYPE_DESCRIPTION_FACTORY
        self.model = model
        self.security = security
        self.short_term_storage_monitor = short_term_storage_monitor

        self.hda_manager = hda_manager
        self.history_manager = history_manager
        self.tag_handler = tag_handler.create_tag_handler_session()
        self.ldda_manager = ldda_manager

    def precreate_dataset_collection_instance(
        self,
        trans,
        parent,
        name,
        structure,
        implicit_inputs=None,
        implicit_output_name=None,
        tags=None,
        completed_collection=None,
    ):
        # TODO: prebuild all required HIDs and send them in so no need to flush in between.
        dataset_collection = self.precreate_dataset_collection(
            structure,
            allow_unitialized_element=implicit_output_name is not None,
            completed_collection=completed_collection,
            implicit_output_name=implicit_output_name,
        )
        instance = self._create_instance_for_collection(
            trans,
            parent,
            name,
            dataset_collection,
            implicit_inputs=implicit_inputs,
            implicit_output_name=implicit_output_name,
            flush=False,
            tags=tags,
        )
        return instance

    def precreate_dataset_collection(
        self, structure, allow_unitialized_element=True, completed_collection=None, implicit_output_name=None
    ):
        has_structure = not structure.is_leaf and structure.children_known
        if not has_structure and allow_unitialized_element:
            dataset_collection = model.DatasetCollectionElement.UNINITIALIZED_ELEMENT
        elif not has_structure:
            collection_type_description = structure.collection_type_description
            dataset_collection = model.DatasetCollection(populated=False)
            dataset_collection.collection_type = collection_type_description.collection_type
        else:
            collection_type_description = structure.collection_type_description
            dataset_collection = model.DatasetCollection(populated=False)
            dataset_collection.collection_type = collection_type_description.collection_type
            elements = []
            for index, (identifier, substructure) in enumerate(structure.children):
                # TODO: Open question - populate these now or later?
                element = None
                if completed_collection and implicit_output_name:
                    job = completed_collection[index]
                    if job:
                        it = (
                            jtiodca.dataset_collection
                            for jtiodca in job.output_dataset_collections
                            if jtiodca.name == implicit_output_name
                        )
                        element = next(it, None)
                if element is None:
                    if substructure.is_leaf:
                        element = model.DatasetCollectionElement.UNINITIALIZED_ELEMENT
                    else:
                        element = self.precreate_dataset_collection(
                            substructure, allow_unitialized_element=allow_unitialized_element
                        )

                element = model.DatasetCollectionElement(
                    collection=dataset_collection,
                    element=element,
                    element_identifier=identifier,
                    element_index=index,
                )
                elements.append(element)
            dataset_collection.element_count = len(elements)

        return dataset_collection

    def create(
        self,
        trans,
        parent,
        name,
        collection_type,
        element_identifiers=None,
        elements=None,
        implicit_collection_info=None,
        trusted_identifiers=None,
        hide_source_items=False,
        tags=None,
        copy_elements=False,
        history=None,
        set_hid=True,
        flush=True,
        completed_job=None,
        output_name=None,
    ):
        """
        PRECONDITION: security checks on ability to add to parent
        occurred during load.
        """
        # Trust embedded, newly created objects created by tool subsystem.
        if trusted_identifiers is None:
            trusted_identifiers = implicit_collection_info is not None

        if element_identifiers and not trusted_identifiers:
            validate_input_element_identifiers(element_identifiers)

        if completed_job and output_name:
            jtodca = next(a for a in completed_job.output_dataset_collection_instances if a.name == output_name)
            dataset_collection = jtodca.dataset_collection_instance.collection
        else:
            dataset_collection = self.create_dataset_collection(
                trans=trans,
                collection_type=collection_type,
                element_identifiers=element_identifiers,
                elements=elements,
                hide_source_items=hide_source_items,
                copy_elements=copy_elements,
                history=history,
            )

        implicit_inputs = []
        if implicit_collection_info:
            implicit_inputs = implicit_collection_info.get("implicit_inputs", [])

        implicit_output_name = None
        if implicit_collection_info:
            implicit_output_name = implicit_collection_info["implicit_output_name"]

        return self._create_instance_for_collection(
            trans,
            parent,
            name,
            dataset_collection,
            implicit_inputs=implicit_inputs,
            implicit_output_name=implicit_output_name,
            tags=tags,
            set_hid=set_hid,
            flush=flush,
        )

    def _create_instance_for_collection(
        self,
        trans,
        parent,
        name,
        dataset_collection,
        implicit_output_name=None,
        implicit_inputs=None,
        tags=None,
        set_hid=True,
        flush=True,
    ):
        if isinstance(parent, model.History):
            dataset_collection_instance: Union[
                model.HistoryDatasetCollectionAssociation,
                model.LibraryDatasetCollectionAssociation,
            ] = model.HistoryDatasetCollectionAssociation(
                collection=dataset_collection,
                name=name,
            )
            assert isinstance(dataset_collection_instance, model.HistoryDatasetCollectionAssociation)
            if implicit_inputs:
                for input_name, input_collection in implicit_inputs:
                    dataset_collection_instance.add_implicit_input_collection(input_name, input_collection)

            if implicit_output_name:
                dataset_collection_instance.implicit_output_name = implicit_output_name

            log.debug("Created collection with %d elements" % (len(dataset_collection_instance.collection.elements)))

            if set_hid:
                parent.add_dataset_collection(dataset_collection_instance)

        elif isinstance(parent, model.LibraryFolder):
            dataset_collection_instance = model.LibraryDatasetCollectionAssociation(
                collection=dataset_collection,
                folder=parent,
                name=name,
            )

        else:
            message = f"Internal logic error - create called with unknown parent type {type(parent)}"
            log.exception(message)
            raise MessageException(message)

        # Tags may be coming in as a dictionary of tag model objects if copying them from other
        # existing Galaxy objects or as a list of strings if the tags are coming from user supplied
        # values.
        if isinstance(tags, list):
            assert implicit_inputs is None, implicit_inputs
            tags = self.tag_handler.add_tags_from_list(trans.user, dataset_collection_instance, tags, flush=False)
        else:
            tags = self._append_tags(dataset_collection_instance, implicit_inputs, tags)
        return self.__persist(dataset_collection_instance, flush=flush)

    def create_dataset_collection(
        self,
        trans,
        collection_type,
        element_identifiers=None,
        elements=None,
        hide_source_items=None,
        copy_elements=False,
        history=None,
    ):
        # Make sure at least one of these is None.
        assert element_identifiers is None or elements is None

        if element_identifiers is None and elements is None:
            raise RequestParameterInvalidException(ERROR_INVALID_ELEMENTS_SPECIFICATION)
        if not collection_type:
            raise RequestParameterInvalidException(ERROR_NO_COLLECTION_TYPE)

        collection_type_description = self.collection_type_descriptions.for_collection_type(collection_type)
        has_subcollections = collection_type_description.has_subcollections()
        # If we have elements, this is an internal request, don't need to load
        # objects from identifiers.
        if elements is None:
            elements = self._element_identifiers_to_elements(
                trans,
                collection_type_description=collection_type_description,
                element_identifiers=element_identifiers,
                hide_source_items=hide_source_items,
                copy_elements=copy_elements,
                history=history,
            )
            if history:
                history.add_pending_items()
        else:
            if has_subcollections:
                # Nested collection - recursively create collections as needed.
                self.__recursively_create_collections_for_elements(
                    trans, elements, hide_source_items, copy_elements=copy_elements, history=history
                )
        # else if elements is set, it better be an ordered dict!

        if elements is not self.ELEMENTS_UNINITIALIZED:
            type_plugin = collection_type_description.rank_type_plugin()
            dataset_collection = builder.build_collection(type_plugin, elements)
        else:
            dataset_collection = model.DatasetCollection(populated=False)
        dataset_collection.collection_type = collection_type
        return dataset_collection

    def get_converters_for_collection(self, trans, id, datatypes_registry: Registry, instance_type="history"):
        dataset_collection_instance = self.get_dataset_collection_instance(
            trans, id=id, instance_type=instance_type, check_ownership=True
        )
        dbkeys_and_extensions = dataset_collection_instance.dataset_dbkeys_and_extensions_summary
        suitable_converters = set()
        first_extension = True
        most_recent_datatype = None
        # TODO error checking
        for datatype in dbkeys_and_extensions[1]:
            new_converters = datatypes_registry.get_converters_by_datatype(datatype)
            set_of_new_converters = set()
            for tgt_type, tgt_val in new_converters.items():
                converter = (tgt_type, tgt_val)
                set_of_new_converters.add(converter)
            if first_extension is True:
                suitable_converters = set_of_new_converters
                most_recent_datatype = datatype
                first_extension = False
            else:
                suitable_converters = suitable_converters.intersection(set_of_new_converters)
                if suitable_converters:
                    most_recent_datatype = datatype
        suitable_tool_ids = list()
        for tool in suitable_converters:
            tool_info = {
                "tool_id": tool[1].id,
                "name": tool[1].name,
                "target_type": tool[0],
                "original_type": most_recent_datatype,
            }
            suitable_tool_ids.append(tool_info)
        return suitable_tool_ids

    def _element_identifiers_to_elements(
        self,
        trans,
        collection_type_description,
        element_identifiers,
        hide_source_items=False,
        copy_elements=False,
        history=None,
    ):
        if collection_type_description.has_subcollections():
            # Nested collection - recursively create collections and update identifiers.
            self.__recursively_create_collections_for_identifiers(
                trans, element_identifiers, hide_source_items, copy_elements, history=history
            )
        new_collection = False
        for element_identifier in element_identifiers:
            if element_identifier.get("src") == "new_collection" and element_identifier.get("collection_type") == "":
                new_collection = True
                elements = self.__load_elements(
                    trans=trans,
                    element_identifiers=element_identifier["element_identifiers"],
                    hide_source_items=hide_source_items,
                    copy_elements=copy_elements,
                    history=history,
                )
        if not new_collection:
            elements = self.__load_elements(
                trans=trans,
                element_identifiers=element_identifiers,
                hide_source_items=hide_source_items,
                copy_elements=copy_elements,
                history=history,
            )
        return elements

    def _append_tags(self, dataset_collection_instance, implicit_inputs=None, tags=None):
        tags = tags or {}
        implicit_inputs = implicit_inputs or []
        for _, v in implicit_inputs:
            for tag in v.auto_propagated_tags:
                tags[tag.value] = tag
        for _, tag in tags.items():
            dataset_collection_instance.tags.append(tag.copy(cls=model.HistoryDatasetCollectionTagAssociation))

    def collection_builder_for(self, dataset_collection):
        return builder.BoundCollectionBuilder(dataset_collection)

    def delete(self, trans, instance_type, id, recursive=False, purge=False):
        dataset_collection_instance = self.get_dataset_collection_instance(
            trans, instance_type, id, check_ownership=True
        )
        dataset_collection_instance.deleted = True
        trans.sa_session.add(dataset_collection_instance)

        if recursive:
            for dataset in dataset_collection_instance.collection.dataset_instances:
                try:
                    self.hda_manager.error_unless_owner(dataset, user=trans.get_user(), current_history=trans.history)
                except HistoryDatasetAssociationNoHistoryException:
                    log.info(
                        f"Cannot delete HistoryDatasetAssociation {dataset.id}, HistoryDatasetAssociation has no associated History, cannot verify owner"
                    )
                    continue
                if not dataset.deleted:
                    dataset.deleted = True

                if purge and not dataset.purged:
                    self.hda_manager.purge(dataset)

        trans.sa_session.flush()

    def update(self, trans, instance_type, id, payload):
        dataset_collection_instance = self.get_dataset_collection_instance(
            trans, instance_type, id, check_ownership=True
        )
        if trans.user is None:
            anon_allowed_payload = {}
            if "deleted" in payload:
                anon_allowed_payload["deleted"] = payload["deleted"]
            if "visible" in payload:
                anon_allowed_payload["visible"] = payload["visible"]
            payload = self._validate_and_parse_update_payload(anon_allowed_payload)
        else:
            payload = self._validate_and_parse_update_payload(payload)
        changed = self._set_from_dict(trans, dataset_collection_instance, payload)
        return changed

    def copy(self, trans, parent, source, encoded_source_id, copy_elements=False, dataset_instance_attributes=None):
        """
        PRECONDITION: security checks on ability to add to parent occurred
        during load.
        """
        assert source == "hdca"  # for now
        source_hdca = self.__get_history_collection_instance(trans, encoded_source_id)
        copy_kwds = {}
        if copy_elements:
            copy_kwds["element_destination"] = parent  # e.g. a history
        if dataset_instance_attributes is not None:
            copy_kwds["dataset_instance_attributes"] = dataset_instance_attributes
        new_hdca = source_hdca.copy(flush=False, **copy_kwds)
        new_hdca.copy_tags_from(target_user=trans.get_user(), source=source_hdca)
        if not copy_elements:
            parent.add_dataset_collection(new_hdca)
        trans.sa_session.flush()
        return new_hdca

    def _set_from_dict(self, trans, dataset_collection_instance, new_data):
        # send what we can down into the model
        changed = dataset_collection_instance.set_from_dict(new_data)

        # the rest (often involving the trans) - do here
        if "annotation" in new_data.keys() and trans.get_user():
            dataset_collection_instance.add_item_annotation(
                trans.sa_session, trans.get_user(), dataset_collection_instance, new_data["annotation"]
            )
            changed["annotation"] = new_data["annotation"]

        # the api promises a list of changed fields, but tags are not marked as changed to avoid the
        # flush, so we must handle changed tag responses manually
        new_tags = None
        if "tags" in new_data.keys() and trans.get_user():
            # set_tags_from_list will flush on its own, no need to add to 'changed' here and incur a second flush.
            new_tags = self.tag_handler.set_tags_from_list(
                trans.get_user(), dataset_collection_instance, new_data["tags"]
            )

        if changed.keys():
            trans.sa_session.flush()

        # set client tag field response after the flush
        if new_tags is not None:
            changed["tags"] = dataset_collection_instance.make_tag_string_list()

        return changed

    def _validate_and_parse_update_payload(self, payload):
        validated_payload = {}
        for key, val in payload.items():
            if val is None:
                continue
            if key in ("name"):
                val = validation.validate_and_sanitize_basestring(key, val)
                validated_payload[key] = val
            if key in ("deleted", "visible"):
                validated_payload[key] = validation.validate_boolean(key, val)
            elif key == "tags":
                validated_payload[key] = validation.validate_and_sanitize_basestring_list(key, val)
        return validated_payload

    def history_dataset_collections(self, history, query):
        collections = history.active_dataset_collections
        collections = list(filter(query.direct_match, collections))
        return collections

    def __persist(self, dataset_collection_instance, flush=True):
        context = self.model.context
        context.add(dataset_collection_instance)
        if flush:
            context.flush()
        return dataset_collection_instance

    def __recursively_create_collections_for_identifiers(
        self, trans, element_identifiers, hide_source_items, copy_elements, history=None
    ):
        for element_identifier in element_identifiers:
            try:
                if element_identifier.get("src") != "new_collection":
                    # not a new collection, keep moving...
                    continue
            except KeyError:
                # Not a dictionary, just an id of an HDA - move along.
                continue

            # element identifier is a dict with src new_collection...
            collection_type = element_identifier.get("collection_type")
            collection = self.create_dataset_collection(
                trans=trans,
                collection_type=collection_type,
                element_identifiers=element_identifier["element_identifiers"],
                hide_source_items=hide_source_items,
                copy_elements=copy_elements,
                history=history,
            )
            element_identifier["__object__"] = collection

        return element_identifiers

    def __recursively_create_collections_for_elements(
        self, trans, elements, hide_source_items, copy_elements, history=None
    ):
        if elements is self.ELEMENTS_UNINITIALIZED:
            return

        new_elements = {}
        for key, element in elements.items():
            if isinstance(element, model.DatasetCollection):
                continue

            if element.get("src") != "new_collection":
                continue

            # element is a dict with src new_collection and
            # and dict of named elements
            collection_type = element.get("collection_type")
            sub_elements = element["elements"]
            collection = self.create_dataset_collection(
                trans=trans,
                collection_type=collection_type,
                elements=sub_elements,
                hide_source_items=hide_source_items,
                copy_elements=copy_elements,
                history=history,
            )
            new_elements[key] = collection
        elements.update(new_elements)

    def __load_elements(self, trans, element_identifiers, hide_source_items=False, copy_elements=False, history=None):
        elements = {}
        for element_identifier in element_identifiers:
            elements[element_identifier["name"]] = self.__load_element(
                trans,
                element_identifier=element_identifier,
                hide_source_items=hide_source_items,
                copy_elements=copy_elements,
                history=history,
            )
        return elements

    def __load_element(self, trans, element_identifier, hide_source_items, copy_elements, history=None):
        # if not isinstance( element_identifier, dict ):
        #    # Is allowing this to just be the id of an hda too clever? Somewhat
        #    # consistent with other API methods though.
        #    element_identifier = dict( src='hda', id=str( element_identifier ) )

        # Previously created collection already found in request, just pass
        # through as is.
        if "__object__" in element_identifier:
            the_object = element_identifier["__object__"]
            if the_object is not None and the_object.id:
                context = self.model.context
                if the_object not in context:
                    the_object = context.query(type(the_object)).get(the_object.id)
            return the_object

        # dataset_identifier is dict {src=hda|ldda|hdca|new_collection, id=<encoded_id>}
        try:
            src_type = element_identifier.get("src", "hda")
        except AttributeError:
            raise MessageException(f"Dataset collection element definition ({element_identifier}) not dictionary-like.")
        encoded_id = element_identifier.get("id")
        if not src_type or not encoded_id:
            message_template = "Problem decoding element identifier %s - must contain a 'src' and a 'id'."
            message = message_template % element_identifier
            raise RequestParameterInvalidException(message)

        tags = element_identifier.pop("tags", None)
        tag_str = ""
        if tags:
            tag_str = ",".join(str(_) for _ in tags)
        if src_type == "hda":
            decoded_id = int(trans.app.security.decode_id(encoded_id))
            hda = self.hda_manager.get_accessible(decoded_id, trans.user)
            if copy_elements:
                element = self.hda_manager.copy(hda, history=history or trans.history, hide_copy=True, flush=False)
            else:
                element = hda
            if hide_source_items and self.hda_manager.get_owned(
                hda.id, user=trans.user, current_history=history or trans.history
            ):
                hda.visible = False
            self.tag_handler.apply_item_tags(user=trans.user, item=element, tags_str=tag_str, flush=False)
        elif src_type == "ldda":
            element = self.ldda_manager.get(trans, encoded_id, check_accessible=True)
            element = element.to_history_dataset_association(
                history or trans.history, add_to_history=True, visible=not hide_source_items
            )
            self.tag_handler.apply_item_tags(user=trans.user, item=element, tags_str=tag_str, flush=False)
        elif src_type == "hdca":
            # TODO: Option to copy? Force copy? Copy or allow if not owned?
            element = self.__get_history_collection_instance(trans, encoded_id).collection
        # TODO: ldca.
        else:
            raise RequestParameterInvalidException(f"Unknown src_type parameter supplied '{src_type}'.")
        return element

    def match_collections(self, collections_to_match):
        """
        May seem odd to place it here, but planning to grow sophistication and
        get plugin types involved so it will likely make sense in the future.
        """
        return MatchingCollections.for_collections(collections_to_match, self.collection_type_descriptions)

    def get_dataset_collection_instance(self, trans, instance_type, id, **kwds):
        """ """
        if instance_type == "history":
            return self.__get_history_collection_instance(trans, id, **kwds)
        elif instance_type == "library":
            return self.__get_library_collection_instance(trans, id, **kwds)

    def get_dataset_collection(self, trans, encoded_id):
        collection_id = int(trans.app.security.decode_id(encoded_id))
        collection = trans.sa_session.query(trans.app.model.DatasetCollection).get(collection_id)
        return collection

    def apply_rules(self, hdca, rule_set, handle_dataset):
        hdca_collection = hdca.collection
        collection_type = hdca_collection.collection_type
        elements = hdca_collection.elements
        collection_type_description = self.collection_type_descriptions.for_collection_type(collection_type)
        initial_data, initial_sources = self.__init_rule_data(elements, collection_type_description)
        data, sources = rule_set.apply(initial_data, initial_sources)

        collection_type = rule_set.collection_type
        collection_type_description = self.collection_type_descriptions.for_collection_type(collection_type)
        elements = self._build_elements_from_rule_data(
            collection_type_description, rule_set, data, sources, handle_dataset
        )
        return elements

    def _build_elements_from_rule_data(self, collection_type_description, rule_set, data, sources, handle_dataset):
        identifier_columns = rule_set.identifier_columns
        mapping_as_dict = rule_set.mapping_as_dict
        elements: Dict[str, Any] = {}
        for data_index, row_data in enumerate(data):
            # For each row, find place in depth for this element.
            collection_type_at_depth = collection_type_description
            elements_at_depth = elements

            for i, identifier_column in enumerate(identifier_columns):
                identifier = row_data[identifier_column]

                if i + 1 == len(identifier_columns):
                    # At correct final position in nested structure for this dataset.
                    if collection_type_at_depth.collection_type == "paired":
                        if identifier.lower() in ["f", "1", "r1", "forward"]:
                            identifier = "forward"
                        elif identifier.lower() in ["r", "2", "r2", "reverse"]:
                            identifier = "reverse"
                        else:
                            raise Exception(
                                "Unknown indicator of paired status encountered - only values of F, R, 1, 2, R1, R2, forward, or reverse are allowed."
                            )

                    tags = []
                    if "group_tags" in mapping_as_dict:
                        columns = mapping_as_dict["group_tags"]["columns"]
                        for tag_column in columns:
                            tag = row_data[tag_column]
                            tags.append(f"group:{tag}")

                    if "tags" in mapping_as_dict:
                        columns = mapping_as_dict["tags"]["columns"]
                        for tag_column in columns:
                            tag = row_data[tag_column]
                            tags.append(tag)

                    effective_dataset = handle_dataset(sources[data_index]["dataset"], tags)
                    elements_at_depth[identifier] = effective_dataset
                    # log.info("Handling dataset [%s] with sources [%s], need to add tags [%s]" % (effective_dataset, sources, tags))
                else:
                    collection_type_at_depth = collection_type_at_depth.child_collection_type_description()
                    found = False
                    if identifier in elements_at_depth:
                        elements_at_depth = elements_at_depth[identifier]["elements"]
                        found = True

                    if not found:
                        # Create a new collection whose elements are defined in the next loop
                        sub_collection: Dict[str, Any] = {}
                        sub_collection["src"] = "new_collection"
                        sub_collection["collection_type"] = collection_type_at_depth.collection_type
                        sub_collection["elements"] = {}
                        # Update elements with new collection
                        elements_at_depth[identifier] = sub_collection
                        # Subsequent loop fills elements of newly created collection
                        elements_at_depth = sub_collection["elements"]

        return elements

    def __init_rule_data(self, elements, collection_type_description, parent_identifiers=None):
        parent_identifiers = parent_identifiers or []
        data: List[List[str]] = []
        sources: List[Dict[str, str]] = []
        for element in elements:
            element_object = element.element_object
            identifiers = parent_identifiers + [element.element_identifier]
            if not element.is_collection:
                data.append([])
                source = {
                    "identifiers": identifiers,
                    "dataset": element_object,
                    "tags": element_object.make_tag_string_list(),
                }
                sources.append(source)
            else:
                child_collection_type_description = collection_type_description.child_collection_type_description()
                element_data, element_sources = self.__init_rule_data(
                    element_object.elements, child_collection_type_description, identifiers
                )
                data.extend(element_data)
                sources.extend(element_sources)

        return data, sources

    def __get_history_collection_instance(self, trans, id, check_ownership=False, check_accessible=True):
        instance_id = trans.app.security.decode_id(id) if isinstance(id, str) else id
        collection_instance = trans.sa_session.query(trans.app.model.HistoryDatasetCollectionAssociation).get(
            instance_id
        )
        if not collection_instance:
            raise RequestParameterInvalidException(f"History dataset collection association {id} not found")
        history = getattr(trans, "history", collection_instance.history)
        if check_ownership:
            self.history_manager.error_unless_owner(collection_instance.history, trans.user, current_history=history)
        if check_accessible:
            self.history_manager.error_unless_accessible(
                collection_instance.history, trans.user, current_history=history
            )
        return collection_instance

    def __get_library_collection_instance(self, trans, id, check_ownership=False, check_accessible=True):
        if check_ownership:
            raise NotImplementedError(
                "Functionality (getting library dataset collection with ownership check) unimplemented."
            )
        instance_id = int(trans.security.decode_id(id))
        collection_instance = trans.sa_session.query(trans.app.model.LibraryDatasetCollectionAssociation).get(
            instance_id
        )
        if not collection_instance:
            raise RequestParameterInvalidException(f"Library dataset collection association {id} not found")
        if check_accessible:
            if not trans.app.security_agent.can_access_library_item(
                trans.get_current_user_roles(), collection_instance, trans.user
            ):
                raise ItemAccessibilityException(
                    "LibraryDatasetCollectionAssociation is not accessible to the current user", type="error"
                )
        return collection_instance

    def get_collection_contents(self, trans, parent_id, limit=None, offset=None):
        """Find first level of collection contents by containing collection parent_id"""
        contents_qry = self._get_collection_contents_qry(parent_id, limit=limit, offset=offset)
        contents = contents_qry.with_session(trans.sa_session()).all()
        return contents

    def _get_collection_contents_qry(self, parent_id, limit=None, offset=None):
        """Build query to find first level of collection contents by containing collection parent_id"""
        DCE = model.DatasetCollectionElement
        qry = Query(DCE).filter(DCE.dataset_collection_id == parent_id)
        qry = qry.order_by(DCE.element_index)
        qry = qry.options(joinedload("child_collection"), joinedload("hda"))
        if limit is not None:
            qry = qry.limit(int(limit))
        if offset is not None:
            qry = qry.offset(int(offset))
        return qry

    def write_dataset_collection(self, request: PrepareDatasetCollectionDownload):
        short_term_storage_monitor = self.short_term_storage_monitor
        instance_id = request.history_dataset_collection_association_id
        with storage_context(request.short_term_storage_request_id, short_term_storage_monitor) as target:
            collection_instance = self.model.context.query(model.HistoryDatasetCollectionAssociation).get(instance_id)
            with ZipFile(target.path, "w") as zip_f:
                write_dataset_collection(collection_instance, zip_f)
