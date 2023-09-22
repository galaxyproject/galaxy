"""
Deserialize Galaxy resources (hdas, ldas, datasets, genomes, etc.) from
a dictionary of string data/ids (often from a query string).
"""
import json
import logging
import weakref
from typing import (
    Callable,
    Dict,
    Optional,
    Union,
)

import galaxy.exceptions
import galaxy.util
from galaxy.managers import (
    hdas as hda_manager,
    visualizations as visualization_manager,
)
from galaxy.model import (
    HistoryDatasetAssociation,
    LibraryDatasetDatasetAssociation,
    Visualization,
)
from galaxy.util import bunch

log = logging.getLogger(__name__)


ParameterPrimitiveType = Union[int, float, str]
ParameterType = Union[
    ParameterPrimitiveType, HistoryDatasetAssociation, LibraryDatasetDatasetAssociation, Visualization
]


class ResourceParser:
    """
    Given a parameter dictionary (often a converted query string) and a
    configuration dictionary (curr. only VisualizationsRegistry uses this),
    convert the entries in the parameter dictionary into resources (Galaxy
    models, primitive types, lists of either, etc.) and return
    in a new dictionary.

    The keys used to store the new values can optionally be re-mapped to
    new keys (e.g. dataset_id="NNN" -> hda=<HistoryDatasetAssociation>).
    """

    primitive_parsers: Dict[str, Callable[[str], ParameterPrimitiveType]] = {
        "str": lambda param: galaxy.util.sanitize_html.sanitize_html(param),
        "bool": lambda param: galaxy.util.string_as_bool(param),
        "int": int,
        "float": float,
        # 'date'  : lambda param: ,
        "json": (lambda param: json.loads(galaxy.util.sanitize_html.sanitize_html(param))),
    }

    def __init__(self, app, *args, **kwargs):
        self.app = weakref.ref(app)
        self.managers = self._init_managers(app)

    def _init_managers(self, app):
        return bunch.Bunch(
            visualization=app[visualization_manager.VisualizationManager],
            hda=app[hda_manager.HDAManager],
        )

    def parse_parameter_dictionary(self, trans, param_config_dict, query_params, param_modifiers=None):
        """
        Parse all expected params from the query dictionary `query_params`.

        If param is required and not present, raises a `KeyError`.
        """
        # log.debug( 'parse_parameter_dictionary, query_params:\n%s', query_params )

        # parse the modifiers first since they modify the params coming next
        # TODO: this is all really for hda_ldda - which we could replace with model polymorphism
        params_that_modify_other_params = self.parse_parameter_modifiers(trans, param_modifiers, query_params)

        resources = {}
        for param_name, param_config in param_config_dict.items():
            # optionally rename the variable returned, defaulting to the original name
            var_name_in_template = param_config.get("var_name_in_template", param_name)

            # if the param is present, get its value, any param modifiers for that param, and parse it into a resource
            # use try catch here and not caller to fall back on the default value or re-raise if required
            resource = None
            query_val = query_params.get(param_name, None)
            if query_val is not None:
                try:
                    target_param_modifiers = params_that_modify_other_params.get(param_name, None)
                    resource = self.parse_parameter(
                        trans, param_config, query_val, param_modifiers=target_param_modifiers
                    )

                except Exception as exception:
                    if trans.debug:
                        raise
                    else:
                        log.warning(
                            "Exception parsing visualization param from query: %s, %s, (%s) %s",
                            param_name,
                            query_val,
                            str(type(exception)),
                            str(exception),
                        )
                    resource = None

            # here - we've either had no value in the query_params or there was a failure to parse
            #   so: error if required, otherwise get a default (which itself defaults to None)
            if resource is None:
                if param_config["required"]:
                    raise KeyError(f"required param {param_name} not found in URL")
                resource = self.parse_parameter_default(trans, param_config)

            resources[var_name_in_template] = resource

        return resources

    def parse_config(self, trans, param_config_dict, query_params):
        """
        Return `query_params` dict parsing only JSON serializable params.
        Complex params such as models, etc. are left as the original query value.
        Keys in `query_params` not found in the `param_config_dict` will not be
        returned.
        """
        # log.debug( 'parse_config, query_params:\n%s', query_params )
        config = {}
        for param_name, param_config in param_config_dict.items():
            config_val = query_params.get(param_name, None)
            if config_val is not None and param_config["type"] in self.primitive_parsers:
                try:
                    config_val = self.parse_parameter(trans, param_config, config_val)

                except Exception as exception:
                    log.warning(
                        "Exception parsing visualization param from query: "
                        + f"{param_name}, {config_val}, ({str(type(exception))}) {str(exception)}"
                    )
                    config_val = None

            # here - we've either had no value in the query_params or there was a failure to parse
            #   so: if there's a default and it's not None, add it to the config
            if config_val is None:
                if param_config.get("default", None) is None:
                    continue
                config_val = self.parse_parameter_default(trans, param_config)

            config[param_name] = config_val

        return config

    # TODO: I would LOVE to rip modifiers out completely
    def parse_parameter_modifiers(
        self, trans, param_modifiers, query_params
    ) -> Dict[str, Dict[str, Optional[ParameterType]]]:
        """
        Parse and return parameters that are meant to modify other parameters,
        be grouped with them, or are needed to successfully parse other parameters.
        """
        # only one level of modification - down that road lies madness
        # parse the modifiers out of query_params first since they modify the other params coming next
        parsed_modifiers: Dict[str, Dict[str, Optional[ParameterType]]] = {}
        if not param_modifiers:
            return parsed_modifiers
        # precondition: expects a two level dictionary
        # { target_param_name -> { param_modifier_name -> { param_modifier_data }}}
        for target_param_name, modifier_dict in param_modifiers.items():
            target_modifiers: Dict[str, Optional[ParameterType]] = {}
            parsed_modifiers[target_param_name] = target_modifiers

            for modifier_name, modifier_config in modifier_dict.items():
                query_val = query_params.get(modifier_name, None)
                if query_val is not None:
                    modifier = self.parse_parameter(trans, modifier_config, query_val)
                    target_modifiers[modifier_name] = modifier
                else:
                    # TODO: required attr?
                    target_modifiers[modifier_name] = self.parse_parameter_default(trans, modifier_config)

        return parsed_modifiers

    def parse_parameter_default(self, trans, param_config) -> Optional[ParameterType]:
        """
        Parse any default values for the given param, defaulting the default
        to `None`.
        """
        # currently, *default* default is None, so this is quaranteed to be part of the dictionary
        default = param_config["default"]
        # if default is None, do not attempt to parse it
        if default is None:
            return default
        # otherwise, parse (currently param_config['default'] is a string just like query param and needs to be parsed)
        #   this saves us the trouble of parsing the default when the config file is read
        #   (and adding this code to the xml parser)
        return self.parse_parameter(trans, param_config, default)

    def parse_parameter(self, trans, expected_param_data, query_param, recurse=True, param_modifiers=None):
        """
        Use data in `expected_param_data` to parse `query_param` from a string into
        a resource usable directly by a template.
        """
        param_type = expected_param_data.get("type")
        parsed_param: Optional[ParameterType] = None

        if param_type in self.primitive_parsers:
            # TODO: what about param modifiers on primitives?
            parsed_param = self.primitive_parsers[param_type](query_param)

        # TODO: constrain_to: this gets complicated - remove?

        # db models
        elif param_type == "visualization":
            # ?: is this even used anymore/anywhere?
            decoded_visualization_id = trans.security.decode_id(query_param, object_name=param_type)
            parsed_param = self.managers.visualization.get_accessible(decoded_visualization_id, trans.user)

        elif param_type == "dataset":
            decoded_dataset_id = trans.security.decode_id(query_param, object_name=param_type)
            parsed_param = self.managers.hda.get_accessible(decoded_dataset_id, trans.user)

        elif param_type == "hda_or_ldda":
            encoded_dataset_id = query_param
            # needs info from another param...
            hda_ldda = param_modifiers.get("hda_ldda")
            if hda_ldda == "hda":
                decoded_dataset_id = trans.security.decode_id(query_param, object_name="dataset")
                parsed_param = self.managers.hda.get_accessible(decoded_dataset_id, trans.user)
            else:
                parsed_param = self.managers.ldda.get(trans, encoded_dataset_id)

        # TODO: ideally this would check v. a list of valid dbkeys
        elif param_type == "dbkey":
            dbkey = query_param
            parsed_param = galaxy.util.sanitize_html.sanitize_html(dbkey)

        return parsed_param
