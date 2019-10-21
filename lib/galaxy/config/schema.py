from galaxy.util.yaml_util import (
    OPTION_DEFAULTS,
    ordered_load,
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

    def __init__(self, schema_path, app_name):
        self.raw_schema = self._read_schema(schema_path)
        self.description = self.raw_schema.get("desc", None)
        app_schema = self.raw_schema['mapping'][app_name]['mapping']
        super(AppSchema, self).__init__(app_schema)

    def _read_schema(self, path):
        with open(path, "r") as f:
            return ordered_load(f)
