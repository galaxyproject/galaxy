from galaxy.util.yaml_util import (
    ordered_load,
    OPTION_DEFAULTS,
)


UNKNOWN_OPTION = {
    "type": "str",
    "required": False,
    "unknown_option": True,
    "desc": "Unknown option, may want to remove or report to Galaxy team."
}


class Schema(object):

    def __init__(self, mapping):
        self.app_schema = mapping

    def get_app_option(self, name):
        try:
            raw_option = self.app_schema[name]
        except KeyError:
            raw_option = UNKNOWN_OPTION
        option = OPTION_DEFAULTS.copy()
        option.update(raw_option)
        return option


class AppSchema(Schema):

    def __init__(self, app_desc):
        self.raw_schema = self._read_schema(app_desc.schema_path)
        self.description = self.raw_schema.get("desc", None)
        app_schema = self.raw_schema['mapping'][app_desc.app_name]['mapping']
        super(AppSchema, self).__init__(app_schema)
        self.reloadable_options = self._load_reloadable_options(app_schema)  # TODO redo

    def _read_schema(self, path):
        with open(path, "r") as f:
            return ordered_load(f)

    def get_reloadable_option_defaults(self):  # TODO redo
        option_dict = {}
        for key in self.reloadable_options:
            option_dict[key] = self.get_app_option(key)["default"]
        return option_dict

    def _load_reloadable_options(self, mapping):  # TODO redo
        reloadable_options = []
        for key, option in mapping.items():
            if option.get("reloadable", False):
                reloadable_options.append(key)
        return reloadable_options
