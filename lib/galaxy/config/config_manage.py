import argparse
import math
import os
import shutil
import sys
import tempfile
from io import StringIO
from textwrap import TextWrapper
from typing import (
    Any,
    List,
    NamedTuple,
)

import yaml
from boltons.iterutils import remap

try:
    from gravity.util import settings_to_sample
except ImportError:
    settings_to_sample = None

try:
    from pykwalify.core import Core
except ImportError:
    Core = None

if __name__ == "__main__":
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir)))


from galaxy.config import (
    GALAXY_CONFIG_SCHEMA_PATH,
    REPORTS_CONFIG_SCHEMA_PATH,
    TOOL_SHED_CONFIG_SCHEMA_PATH,
)
from galaxy.config.schema import (
    AppSchema,
    OPTION_DEFAULTS,
)
from galaxy.util import safe_makedirs
from galaxy.util.properties import nice_config_parser
from galaxy.util.yaml_util import (
    ordered_dump,
    ordered_load,
)

DESCRIPTION = "Convert configuration files."

APP_DESCRIPTION = """Application to target for operation (i.e. galaxy, tool_shed, or reports))"""
DRY_RUN_DESCRIPTION = """If this action modifies files, just print what would be the result and continue."""
UNKNOWN_OPTION_MESSAGE = "Option [%s] not found in schema - either it is invalid or the Galaxy team hasn't documented it. If invalid, you should manually remove it. If the option is valid but undocumented, please file an issue with the Galaxy team."
USING_SAMPLE_MESSAGE = "Path [%s] not a file, using sample."
EXTRA_SERVER_MESSAGE = "Additional server section after [%s] encountered [%s], will be ignored."
MISSING_FILTER_TYPE_MESSAGE = "Missing filter type for section [%s], it will be ignored."
UNHANDLED_FILTER_TYPE_MESSAGE = "Unhandled filter type encountered [%s] for section [%s]."
NO_APP_MAIN_MESSAGE = "No app:main section found, using application defaults throughout."
YAML_COMMENT_WRAPPER = TextWrapper(
    initial_indent="# ", subsequent_indent="# ", break_long_words=False, break_on_hyphens=False
)
RST_DESCRIPTION_WRAPPER = TextWrapper(
    initial_indent="    ", subsequent_indent="    ", break_long_words=False, break_on_hyphens=False
)
DROP_OPTION_VALUE = object()


class _OptionAction:
    def converted(self, args, app_desc, key, value):
        pass

    def lint(self, args, app_desc, key, value):
        pass


class _DeprecatedAction(_OptionAction):
    def lint(self, args, app_desc, key, value):
        print(f"Option [{key}] has been deprecated, this will likely be dropped in future releases of Galaxy.")


class _DeprecatedAndDroppedAction(_OptionAction):
    def converted(self, args, app_desc, key, value):
        print(f"Option [{key}] has been deprecated and dropped. It is not included in converted configuration.")
        return DROP_OPTION_VALUE

    def lint(self, args, app_desc, key, value):
        print(f"Option [{key}] has been deprecated. Option should be dropped without replacement.")


class _PasteAppFactoryAction(_OptionAction):
    def converted(self, args, app_desc, key, value):
        if value not in app_desc.expected_app_factories:
            raise Exception(f"Ending convert process - unknown paste factory encountered [{value}]")
        return DROP_OPTION_VALUE

    def lint(self, args, app_desc, key, value):
        if value not in app_desc.expected_app_factories:
            print(f"Problem - unknown paste app factory encountered [{value}]")


class _ProductionUnsafe(_OptionAction):
    def __init__(self, unsafe_value):
        self.unsafe_value = unsafe_value

    def lint(self, args, app_desc, key, value):
        if str(value).lower() == str(self.unsafe_value).lower():
            template = "Problem - option [%s] should not be set to [%s] in production environments - it is unsafe."
            message = template % (key, value)
            print(message)


class _ProductionPerformance(_OptionAction):
    def lint(self, args, app_desc, key, value):
        template = "Problem - option [%s] should not be set to [%s] in production environments - it may cause performance issues or instability."
        message = template % (key, value)
        print(message)


class _HandleFilterWithAction(_OptionAction):
    def converted(self, args, app_desc, key, value):
        print("filter-with converted to prefixed module load of uwsgi module, dropping from converted configuration")
        return DROP_OPTION_VALUE


class _RenameAction(_OptionAction):
    def __init__(self, new_name):
        self.new_name = new_name

    def converted(self, args, app_desc, key, value):
        return (self.new_name, value)

    def lint(self, args, app_desc, key, value):
        template = "Problem - option [%s] has been renamed (possibly with slightly different behavior) to [%s]."
        message = template % (key, self.new_name)
        print(message)


OPTION_ACTIONS = {
    "use_beaker_session": _DeprecatedAndDroppedAction(),
    "use_interactive": _DeprecatedAndDroppedAction(),
    "session_type": _DeprecatedAndDroppedAction(),
    "session_data_dir": _DeprecatedAndDroppedAction(),
    "session_key": _DeprecatedAndDroppedAction(),
    "session_secret": _DeprecatedAndDroppedAction(),
    "paste.app_factory": _PasteAppFactoryAction(),
    "filter-with": _HandleFilterWithAction(),
    "debug": _ProductionUnsafe(True),
    "serve_xss_vulnerable_mimetypes": _ProductionUnsafe(True),
    "use_printdebug": _ProductionUnsafe(True),
    "id_secret": _ProductionUnsafe("USING THE DEFAULT IS NOT SECURE!"),
    "master_api_key": _ProductionUnsafe("changethis"),
    "external_service_type_config_file": _DeprecatedAndDroppedAction(),
    "external_service_type_path": _DeprecatedAndDroppedAction(),
    "enable_sequencer_communication": _DeprecatedAndDroppedAction(),
    "run_workflow_toolform_upgrade": _DeprecatedAndDroppedAction(),
    # Next 4 were from library search which is no longer available.
    "enable_lucene_library_search": _DeprecatedAndDroppedAction(),
    "fulltext_max_size": _DeprecatedAndDroppedAction(),
    "fulltext_noindex_filetypes": _DeprecatedAndDroppedAction(),
    "fulltext_url": _DeprecatedAndDroppedAction(),
    "enable_beta_job_managers": _DeprecatedAndDroppedAction(),
    "enable_legacy_sample_tracking_api": _DeprecatedAction(),
    "enable_new_user_preferences": _DeprecatedAndDroppedAction(),
    "force_beta_workflow_scheduled_for_collections": _DeprecatedAndDroppedAction(),
    "force_beta_workflow_scheduled_min_steps": _DeprecatedAndDroppedAction(),
    "history_local_serial_workflow_scheduling": _ProductionPerformance(),
    "allow_library_path_paste": _RenameAction("allow_path_paste"),
    "trust_ipython_notebook_conversion": _RenameAction("trust_jupyter_notebook_conversion"),
    "enable_beta_tool_command_isolation": _DeprecatedAndDroppedAction(),
    "enable_beta_ts_api_install": _DeprecatedAndDroppedAction(),
    "single_user": _ProductionUnsafe(True),
    "tool_submission_burst_threads": _DeprecatedAndDroppedAction(),
    "tool_submission_burst_at": _DeprecatedAndDroppedAction(),
    "toolform_upgrade": _DeprecatedAndDroppedAction(),
    "enable_beta_mulled_containers": _DeprecatedAndDroppedAction(),
    "enable_communication_server": _DeprecatedAndDroppedAction(),
    "communication_server_host": _DeprecatedAndDroppedAction(),
    "communication_server_port": _DeprecatedAndDroppedAction(),
    "persistent_communication_rooms": _DeprecatedAndDroppedAction(),
    "legacy_eager_objectstore_initialization": _DeprecatedAndDroppedAction(),
    "enable_openid": _DeprecatedAndDroppedAction(),
    "openid_consumer_cache_path": _DeprecatedAndDroppedAction(),
}


class App(NamedTuple):
    config_paths: List[str]
    default_port: str
    expected_app_factories: List[str]
    destination: str
    schema_path: str

    @property
    def app_name(self):
        return os.path.splitext(os.path.basename(self.destination))[0]

    @property
    def sample_destination(self):
        return self.destination + ".sample"

    @property
    def schema(self):
        return AppSchema(self.schema_path, self.app_name)


class OptionValue(NamedTuple):
    name: str
    value: Any
    option: Any


GALAXY_APP = App(
    ["universe_wsgi.ini", "config/galaxy.ini"],
    "8080",
    ["galaxy.web.buildapp:app_factory"],
    "config/galaxy.yml",
    str(GALAXY_CONFIG_SCHEMA_PATH),
)
SHED_APP = App(
    ["tool_shed_wsgi.ini", "config/tool_shed.ini"],
    "9009",
    ["tool_shed.webapp.buildapp:app_factory"],
    "config/tool_shed.yml",
    str(TOOL_SHED_CONFIG_SCHEMA_PATH),
)
REPORTS_APP = App(
    ["reports_wsgi.ini", "config/reports.ini"],
    "9001",
    ["galaxy.webapps.reports.buildapp:app_factory"],
    "config/reports.yml",
    str(REPORTS_CONFIG_SCHEMA_PATH),
)
APPS = {"galaxy": GALAXY_APP, "tool_shed": SHED_APP, "reports": REPORTS_APP}


def main(argv=None):
    """Entry point for conversion process."""
    if argv is None:
        argv = sys.argv[1:]
    args = _arg_parser().parse_args(argv)
    app_name = args.app
    app_desc = APPS.get(app_name)
    action = args.action
    action_func = ACTIONS[action]
    action_func(args, app_desc)


def _arg_parser():
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument("action", metavar="ACTION", type=str, choices=list(ACTIONS.keys()), help="action to perform")
    parser.add_argument("app", metavar="APP", type=str, nargs="?", help=APP_DESCRIPTION)
    parser.add_argument("--add-comments", default=False, action="store_true")
    parser.add_argument("--dry-run", default=False, action="store_true", help=DRY_RUN_DESCRIPTION)
    parser.add_argument("--galaxy_root", default=".", type=str)
    return parser


def _to_rst(args, app_desc, heading_level="~"):
    rst = StringIO()
    schema = app_desc.schema
    for key, value in schema.app_schema.items():
        default = None if "default" not in value else value["default"]
        if default is True:
            default = "true"
        elif default is False:
            default = "false"
        option = schema.get_app_option(key)
        option_value = OptionValue(key, default, option)
        _write_option_rst(args, rst, key, heading_level, option_value)
    print(rst.getvalue())


def _write_option_rst(args, rst, key, heading_level, option_value):
    title = f"``{key}``"
    heading = heading_level * len(title)
    rst.write(f"{heading}\n{title}\n{heading}\n\n")
    option, value = _parse_option_value(option_value)
    desc = _get_option_desc(option)
    rst.write(":Description:\n")
    # Wrap and indent desc, replacing whitespaces with a space, except
    # for double newlines which are replaced with a single newline.
    rst.write("\n".join("\n".join(RST_DESCRIPTION_WRAPPER.wrap(_)) for _ in desc.split("\n\n")) + "\n")
    type = option.get("type", None)
    default = option.get("default", "*null*")
    if default is True:
        default = "true"
    elif default is False:
        default = "false"
    elif default == "":
        default = '""'
    rst.write(f":Default: ``{default}``\n")
    if type:
        rst.write(f":Type: {type}\n")
    rst.write("\n\n")


def _find_config(args, app_desc):
    path = os.path.join(args.galaxy_root, app_desc.destination)
    if not os.path.exists(path):
        path = None

        for possible_ini_config_rel in app_desc.config_paths:
            possible_ini_config = os.path.join(args.galaxy_root, possible_ini_config_rel)
            if os.path.exists(possible_ini_config):
                path = possible_ini_config

    if path is None:
        _warn(USING_SAMPLE_MESSAGE % path)
        path = os.path.join(args.galaxy_root, app_desc.sample_destination)

    return path


def _find_app_options(app_desc, path):
    """Load app (as opposed to server) options from specified path.

    Supplied ``path`` may be either YAML or ini file.
    """
    if _is_ini(path):
        p = nice_config_parser(path)
        app_items = _find_app_options_from_config_parser(p)
    else:
        raw_config = _order_load_path(path)
        app_items = raw_config.get(app_desc.app_name, None) or {}
    return app_items


def _find_app_options_from_config_parser(p):
    if not p.has_section("app:main"):
        _warn(NO_APP_MAIN_MESSAGE)
        app_items = {}
    else:
        app_items = dict(p.items("app:main"))

    return app_items


def _lint(args, app_desc):
    path = _find_config(args, app_desc)
    if not os.path.exists(path):
        raise Exception(f"Expected configuration file [{path}] not found.")
    app_items = _find_app_options(app_desc, path)
    for key, value in app_items.items():
        option_action = OPTION_ACTIONS.get(key)
        if option_action is not None:
            option_action.lint(args, app_desc, key, value)


def _validate(args, app_desc):
    if Core is None:
        raise Exception("Cannot validate file, pykwalify is not installed.")
    path = _find_config(args, app_desc)
    # Allow empty mapping (not allowed by pykwalify)
    raw_config = _order_load_path(path)
    if raw_config.get(app_desc.app_name) is None:
        raw_config[app_desc.app_name] = {}
    # Rewrite the file any way to merge any duplicate keys
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".yml") as config_p:
        ordered_dump(raw_config, config_p)

    def _clean(p, k, v):
        return k not in ["reloadable", "path_resolves_to", "per_host"]

    clean_schema = remap(app_desc.schema.raw_schema, _clean)
    with tempfile.NamedTemporaryFile("w", suffix=".yml") as fp:
        ordered_dump(clean_schema, fp)
        fp.flush()
        c = Core(
            source_file=config_p.name,
            schema_files=[fp.name],
        )
    os.remove(config_p.name)
    c.validate()


class PrefixFilter:
    def __init__(self, name, prefix):
        self.name = name
        self.prefix = prefix


class GzipFilter:
    def __init__(self, name):
        self.name = name


def _run_conversion(args, app_desc):
    ini_config = _find_config(args, app_desc)
    if ini_config and not _is_ini(ini_config):
        _warn(f"Cannot convert YAML file {ini_config}, this option is only for ini config files.")
        sys.exit(1)
    elif not ini_config:
        _warn("Failed to find a config to convert - exiting without changes.")
        sys.exit(1)

    p = nice_config_parser(ini_config)
    app_items = _find_app_options_from_config_parser(p)
    app_dict = {}
    schema = app_desc.schema
    for key, value in app_items.items():
        if key in ["__file__", "here"]:
            continue

        if key in OPTION_ACTIONS:
            option_action = OPTION_ACTIONS.get(key)
            new_value = option_action.converted(args, app_desc, key, value)
            if new_value:
                if isinstance(new_value, tuple):
                    key, value = new_value
                else:
                    value = new_value

        if value is DROP_OPTION_VALUE:
            continue

        option = schema.get_app_option(key)
        if option["unknown_option"]:
            _warn(UNKNOWN_OPTION_MESSAGE % key)

        option_value = OptionValue(key, value, option)
        app_dict[key] = option_value

    f = StringIO()
    _write_section(args, f, app_desc.app_name, app_dict)
    destination = os.path.join(args.galaxy_root, app_desc.destination)
    _replace_file(args, f, app_desc, ini_config, destination)


def _is_ini(path):
    return path.endswith(".ini") or path.endswith(".ini.sample")


def _replace_file(args, f, app_desc, from_path, to_path):
    _write_to_file(args, f, to_path)
    backup_path = f"{from_path}.backup"
    print(f"Moving [{from_path}] to [{backup_path}]")
    if args.dry_run:
        print("... skipping because --dry-run is enabled.")
    else:
        shutil.move(from_path, backup_path)


def _build_sample_yaml(args, app_desc):
    schema = app_desc.schema
    f = StringIO()
    description = getattr(schema, "description", None)
    if description:
        description = description.lstrip()
        as_comment = "\n".join(f"# {line}" for line in description.split("\n")) + "\n"
        f.write(as_comment)
    if app_desc.app_name == "galaxy":
        if settings_to_sample is None:
            raise Exception("Please install gravity to rebuild the sample config")
        f.write(settings_to_sample())
    _write_sample_section(args, f, app_desc.app_name, schema)
    destination = os.path.join(args.galaxy_root, app_desc.sample_destination)
    _write_to_file(args, f, destination)


def _write_to_file(args, f, path):
    if hasattr(f, "getvalue"):
        contents = f.getvalue()
    else:
        contents = f
    if args.dry_run:
        contents_indented = "\n".join(f" |{line}" for line in contents.splitlines())
        print(f"Overwriting {path} with the following contents:\n{contents_indented}")
        print("... skipping because --dry-run is enabled.")
    else:
        print(f"Overwriting {path}")
        safe_makedirs(os.path.dirname(path))
        with open(path, "w") as to_f:
            to_f.write(contents)


def _order_load_path(path):
    """Load (with ``_ordered_load``) on specified path (a YAML file)."""
    with open(path) as f:
        # Allow empty mapping (not allowed by pykwalify)
        raw_config = ordered_load(f)
        return raw_config


def _write_sample_section(args, f, section_header, schema, as_comment=True):
    _write_header(f, section_header)
    for key, value in schema.app_schema.items():
        default = None if "default" not in value else value["default"]
        option = schema.get_app_option(key)
        option_value = OptionValue(key, default, option)
        key = option.get("key", key)
        _write_option(args, f, key, option_value, as_comment=as_comment)


def _write_section(args, f, section_header, section_dict):
    _write_header(f, section_header)
    for key, option_value in section_dict.items():
        _write_option(args, f, key, option_value)


def _write_header(f, section_header):
    f.write(f"{section_header}:\n\n")


def _write_option(args, f, key, option_value, as_comment=False):
    option, value = _parse_option_value(option_value)
    desc = _get_option_desc(option)
    comment = ""
    if desc and args.add_comments:
        # Wrap and comment desc, replacing whitespaces with a space, except
        # for double newlines which are replaced with a single newline.
        comment += "\n".join("\n".join(YAML_COMMENT_WRAPPER.wrap(_)) for _ in desc.split("\n\n")) + "\n"
    as_comment_str = "#" if as_comment else ""
    key_val_str = yaml.dump({key: value}, width=math.inf).lstrip("{").rstrip("\n}")
    lines = f"{comment}{as_comment_str}{key_val_str}"
    lines_idented = "\n".join(f"  {line}" for line in lines.split("\n"))
    f.write(f"{lines_idented}\n\n")


def _parse_option_value(option_value):
    if isinstance(option_value, OptionValue):
        option = option_value.option
        value = option_value.value
        # Hack to get nicer YAML values during conversion
        if option.get("type", "str") == "bool":
            value = str(value).lower() == "true"
        elif option.get("type", "str") == "int":
            if value is None:
                raise Exception(f"Failed to parse value for {option}, expected int got None")
            value = int(value)
    else:
        value = option_value
        option = OPTION_DEFAULTS
    return option, value


def _warn(message):
    print(f"WARNING: {message}")


def _get_option_desc(option):
    desc = option["desc"]
    parent_dir = option.get("path_resolves_to")
    if parent_dir:
        path_resolves = f"The value of this option will be resolved with respect to <{parent_dir}>."
        return f"{desc}\n{path_resolves}" if desc else path_resolves
    return desc


ACTIONS = {
    "convert": _run_conversion,
    "build_sample_yaml": _build_sample_yaml,
    "validate": _validate,
    "lint": _lint,
    "build_rst": _to_rst,
}


if __name__ == "__main__":
    main()
