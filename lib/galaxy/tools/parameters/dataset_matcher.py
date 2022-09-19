from logging import getLogger

import galaxy.model

log = getLogger(__name__)


def set_dataset_matcher_factory(trans, tool):
    trans.dataset_matcher_factory = DatasetMatcherFactory(trans, tool)


def unset_dataset_matcher_factory(trans):
    trans.dataset_matcher_factory = None


def get_dataset_matcher_factory(trans):
    dataset_matcher_factory = getattr(trans, "dataset_matcher_factory", None)
    return dataset_matcher_factory or DatasetMatcherFactory(trans)


class DatasetMatcherFactory:
    """"""

    def __init__(self, trans, tool=None):
        self._trans = trans
        self._tool = tool
        self._data_inputs = []
        self._matches_format_cache = {}
        if tool:
            valid_input_states = tool.valid_input_states
        else:
            valid_input_states = galaxy.model.Dataset.valid_input_states
        self.valid_input_states = valid_input_states
        can_process_summary = False
        if tool is not None:
            for input in tool.inputs.values():
                self._collect_data_inputs(input)

            require_public = self._tool and self._tool.tool_type == "data_destination"
            if not require_public and self._data_inputs:
                can_process_summary = True
                for data_input in self._data_inputs:
                    if data_input.options:
                        can_process_summary = False
                        break
        self._can_process_summary = can_process_summary

    def matches_any_format(self, hda_extension, formats):
        for format in formats:
            if self.matches_format(hda_extension, format):
                return True
        return False

    def matches_format(self, hda_extension, format):
        # cache datatype checking combinations for fast recall
        if hda_extension not in self._matches_format_cache:
            self._matches_format_cache[hda_extension] = {}

        formats = self._matches_format_cache[hda_extension]
        if format not in formats:
            datatype = galaxy.model.datatype_for_extension(
                hda_extension, datatypes_registry=self._trans.app.datatypes_registry
            )
            formats[format] = datatype.matches_any([format])

        return formats[format]

    def _collect_data_inputs(self, input):
        type_name = input.type
        if type_name == "repeat" or type_name == "upload_dataset" or type_name == "section":
            for child_input in input.inputs.values():
                self._collect_data_inputs(child_input)
        elif type_name == "conditional":
            for case in input.cases:
                for child_input in case.inputs.values():
                    self._collect_data_inputs(child_input)
        elif type_name == "data" or type_name == "data_collection":
            self._data_inputs.append(input)

    def dataset_matcher(self, param, other_values):
        return DatasetMatcher(self, self._trans, param, other_values)

    def dataset_collection_matcher(self, dataset_matcher):
        if self._can_process_summary:
            return SummaryDatasetCollectionMatcher(self, self._trans, dataset_matcher)
        else:
            return DatasetCollectionMatcher(self._trans, dataset_matcher)


class DatasetMatcher:
    """Utility class to aid DataToolParameter and similar classes in reasoning
    about what HDAs could match or are selected for a parameter and value.

    Goal here is to both encapsulate and reuse logic related to filtering,
    datatype matching, hiding errored dataset, finding implicit conversions,
    and permission handling.
    """

    def __init__(self, dataset_matcher_factory, trans, param, other_values):
        self.dataset_matcher_factory = dataset_matcher_factory
        self.trans = trans
        self.param = param
        self.tool = param.tool
        filter_values = set()
        if param.options and other_values:
            try:
                for v in param.options.get_options(trans, other_values):
                    filter_values.add(v[0])
            except IndexError:
                pass  # no valid options
        self.filter_values = filter_values

    def valid_hda_match(self, hda, check_implicit_conversions=True):
        """Return False if this parameter can not be matched to the supplied
        HDA, otherwise return a description of the match (either a
        HdaDirectMatch describing a direct match or a HdaImplicitMatch
        describing an implicit conversion.)
        """
        rval = False
        formats = self.param.formats
        direct_match, target_ext, converted_dataset = hda.find_conversion_destination(formats)
        if direct_match:
            rval = HdaDirectMatch(hda)
        else:
            if not check_implicit_conversions:
                return False
            if target_ext:
                original_hda = hda
                if converted_dataset:
                    hda = converted_dataset
                rval = HdaImplicitMatch(hda, target_ext, original_hda)
            else:
                return False
        if self.filter(hda):
            return False
        return rval

    def hda_match(self, hda, check_implicit_conversions=True, ensure_visible=True):
        """If HDA is accessible, return information about whether it could
        match this parameter and if so how. See valid_hda_match for more
        information.
        """
        dataset = hda.dataset
        valid_state = dataset.state in self.dataset_matcher_factory.valid_input_states
        if valid_state and (not ensure_visible or hda.visible):
            # If we are sending data to an external application, then we need to make sure there are no roles
            # associated with the dataset that restrict its access from "public".
            require_public = self.tool and self.tool.tool_type == "data_destination"
            if require_public and not self.trans.app.security_agent.dataset_is_public(dataset):
                return False
            return self.valid_hda_match(hda, check_implicit_conversions=check_implicit_conversions)

    def filter(self, hda):
        """Filter out this value based on other values for job (if
        applicable).
        """
        param = self.param
        return param.options and param.get_options_filter_attribute(hda) not in self.filter_values


class HdaDirectMatch:
    """Supplied HDA was a valid option directly (did not need to find implicit
    conversion).
    """

    def __init__(self, hda):
        self.hda = hda

    @property
    def implicit_conversion(self):
        return False


class HdaImplicitMatch:
    """Supplied HDA was a valid option directly (did not need to find implicit
    conversion).
    """

    def __init__(self, hda, target_ext, original_hda):
        self.original_hda = original_hda
        self.hda = hda
        self.target_ext = target_ext

    @property
    def implicit_conversion(self):
        return True


class HdcaDirectMatch:
    implicit_conversion = False

    def __init__(self):
        pass


class HdcaImplicitMatch:
    implicit_conversion = True

    def __init__(self):
        pass


class SummaryDatasetCollectionMatcher:
    def __init__(self, dataset_matcher_factory, trans, dataset_matcher):
        self.dataset_matcher_factory = dataset_matcher_factory
        self._trans = trans
        self.dataset_matcher = dataset_matcher

    def hdca_match(self, history_dataset_collection_association):
        dataset_collection = history_dataset_collection_association.collection

        if not dataset_collection.populated_optimized:
            return False

        (states, extensions) = dataset_collection.dataset_states_and_extensions_summary
        for state in states:
            if state not in self.dataset_matcher_factory.valid_input_states:
                return False

        formats = self.dataset_matcher.param.formats
        uses_implicit_conversion = False
        for extension in extensions:
            datatypes_registry = self._trans.app.datatypes_registry
            direct_match, converted_ext, _ = datatypes_registry.find_conversion_destination_for_dataset_by_extensions(
                extension, formats
            )
            if direct_match:
                continue
            if not converted_ext:
                return False
            else:
                uses_implicit_conversion = True

        return HdcaImplicitMatch() if uses_implicit_conversion else HdcaDirectMatch()


class DatasetCollectionMatcher:
    def __init__(self, trans, dataset_matcher):
        self.dataset_matcher = dataset_matcher
        self._trans = trans

    def __valid_element(self, element):
        # Simplify things for now and assume these are hdas and not implicit
        # converts. One could imagine handling both of those cases down the
        # road.
        if element.ldda:
            return False

        child_collection = element.child_collection
        if child_collection:
            return self.dataset_collection_match(child_collection)

        hda = element.hda
        if not hda:
            return False
        hda_match = self.dataset_matcher.hda_match(hda, ensure_visible=False)
        return hda_match

    def hdca_match(self, history_dataset_collection_association):
        dataset_collection = history_dataset_collection_association.collection
        return self.dataset_collection_match(dataset_collection)

    def dataset_collection_match(self, dataset_collection):
        # If dataset collection not yet populated, cannot determine if it
        # would be a valid match for this parameter.
        if not dataset_collection.populated:
            return False

        valid = True
        uses_implicit_conversion = False
        for element in dataset_collection.elements:
            match_element = self.__valid_element(element)
            if not match_element:
                valid = False
                break
            elif match_element.implicit_conversion:
                uses_implicit_conversion = True

        return valid and (HdcaImplicitMatch() if uses_implicit_conversion else HdcaDirectMatch())


__all__ = ("get_dataset_matcher_factory", "set_dataset_matcher_factory", "unset_dataset_matcher_factory")
