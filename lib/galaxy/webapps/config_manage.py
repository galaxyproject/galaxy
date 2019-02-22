from __future__ import absolute_import, print_function

import argparse
import os
import shutil
import string
import sys
import tempfile
from collections import (
    namedtuple,
    OrderedDict
)
from textwrap import TextWrapper

import requests
import six
import yaml
from six import StringIO

try:
    from pykwalify.core import Core
except ImportError:
    Core = None

if __name__ == '__main__':
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir)))

from galaxy.util import safe_makedirs
from galaxy.util.properties import nice_config_parser

DESCRIPTION = "Convert configuration files."

APP_DESCRIPTION = """Application to target for operation (i.e. galaxy, tool_shed, or reports))"""
DRY_RUN_DESCRIPTION = """If this action modifies files, just print what would be the result and continue."""
UNKNOWN_OPTION_MESSAGE = "Option [%s] not found in schema - either it is invalid or the Galaxy team hasn't documented it. If invalid, you should manually remove it. If the option is valid but undocumented, please file an issue with the Galaxy team."
USING_SAMPLE_MESSAGE = "Path [%s] not a file, using sample."
EXTRA_SERVER_MESSAGE = "Additional server section after [%s] encountered [%s], will be ignored."
MISSING_FILTER_TYPE_MESSAGE = "Missing filter type for section [%s], it will be ignored."
UNHANDLED_FILTER_TYPE_MESSAGE = "Unhandled filter type encountered [%s] for section [%s]."
NO_APP_MAIN_MESSAGE = "No app:main section found, using application defaults throughout."
YAML_COMMENT_WRAPPER = TextWrapper(initial_indent="# ", subsequent_indent="# ")
RST_DESCRIPTION_WRAPPER = TextWrapper(initial_indent="    ", subsequent_indent="    ")
UWSGI_SCHEMA_PATH = "lib/galaxy/webapps/uwsgi_schema.yml"

App = namedtuple(
    "App",
    ["config_paths", "default_port", "expected_app_factories", "destination", "schema_path", "uwsgi_module"]
)

UWSGI_OPTIONS = OrderedDict([
    ('http', {
        'desc': """The address and port on which to listen.  By default, only listen to localhost ($app_name will not be accessible over the network).  Use ':$default_port' to listen on all available network interfaces.""",
        'default': '127.0.0.1:$default_port',
        'type': 'str',
    }),
    ('buffer-size', {
        'desc': """By default uWSGI allocates a very small buffer (4096 bytes) for the headers of each request. If you start receiving "invalid request block size" in your logs, it could mean you need a bigger buffer. We recommend at least 16384.""",
        'default': 16384,
        'type': 'int',
    }),
    ('processes', {
        'desc': """Number of web server (worker) processes to fork after the application has loaded. If this is set to greater than 1, thunder-lock likely should be enabled below.""",
        'default': 1,
        'type': 'int',
    }),
    ('threads', {
        'desc': """Number of threads for each web server process.""",
        'default': 4,
        'type': 'int',
    }),
    ('offload-threads', {
        'desc': """Number of threads for serving static content and handling internal routing requests.""",
        'default': 2,
        'type': 'int',
    }),
    ('static-map.1', {
        'key': 'static-map',
        'desc': """Mapping to serve style content.""",
        'default': '/static/style=static/style/blue',
        'type': 'str',
    }),
    ('static-map.2', {
        'key': 'static-map',
        'desc': """Mapping to serve the remainder of the static content.""",
        'default': '/static=static',
        'type': 'str',
    }),
    ('static-map.3', {
        'key': 'static-map',
        'desc': """Mapping to serve the favicon.""",
        'default': '/favicon.ico=static/favicon.ico',
        'type': 'str',
    }),
    ('master', {
        'desc': """Enable the master process manager. Disabled by default for maximum compatibility with CTRL+C, but should be enabled for use with --daemon and/or production deployments.""",
        'default': False,
        'type': 'bool',
    }),
    ('virtualenv', {
        'desc': """Path to the application's Python virtual environment. If using Conda for Galaxy's framework dependencies (not tools!), do not set this.""",
        'default': '.venv',
        'type': 'str',
    }),
    ('pythonpath', {
        'desc': """Path to the application's Python library.""",
        'default': 'lib',
        'type': 'str',
    }),
    ('module', {
        'desc': """The entry point which returns the web application (e.g. Galaxy, Reports, etc.) that you are loading.""",
        'default': '$uwsgi_module',
        'type': 'str',
    }),
    ('#mount', {
        'desc': """Mount the web application (e.g. Galaxy, Reports, etc.) at the given URL prefix. Cannot be used together with 'module:' above.""",
        'default': '/galaxy=galaxy.webapps.galaxy.buildapp:uwsgi_app()',
        'type': 'str',
    }),
    ('manage-script-name', {
        'desc': """Make uWSGI rewrite PATH_INFO and SCRIPT_NAME according to mount-points. Set this to true if a URL prefix is used.""",
        'default': False,
        'type': 'bool',
    }),
    ('thunder-lock', {
        'desc': """It is usually a good idea to set this to ``true`` if processes is greater than 1.""",
        'default': False,
        'type': 'bool',
    }),
    ('die-on-term', {
        'desc': """Cause uWSGI to respect the traditional behavior of dying on SIGTERM (its default is to brutally reload workers)""",
        'default': True,
        'type': 'bool',
    }),
    ('hook-master-start.1', {
        'key': 'hook-master-start',
        'desc': """Cause uWSGI to gracefully reload workers and mules upon receipt of SIGINT (its default is to brutally kill workers)""",
        'default': 'unix_signal:2 gracefully_kill_them_all',
        'type': 'str',
    }),
    ('hook-master-start.2', {
        'key': 'hook-master-start',
        'desc': """Cause uWSGI to gracefully reload workers and mules upon receipt of SIGTERM (its default is to brutally kill workers)""",
        'default': 'unix_signal:15 gracefully_kill_them_all',
        'type': 'str',
    }),
    ('py-call-osafterfork', {
        'desc': """Feature necessary for proper mule signal handling""",
        'default': True,
        'type': 'bool',
    }),
    ('enable-threads', {
        'desc': """Ensure application threads will run if `threads` is unset.""",
        'default': True,
        'type': 'bool',
    }),
    # ('route-uri', {
    #     'default': '^/proxy/ goto:proxy'
    # }),
    # ('route', {
    #     'default': '.* last:'
    # }),
    # ('route-label', {
    #     'default': 'proxy'
    # }),
    # ('route-run', {
    #     'default': 'rpcvar:TARGET_HOST galaxy_dynamic_proxy_mapper ${HTTP_HOST} ${cookie[galaxysession]}'
    # }),
    # ('route-run', {
    #     'default': "['log:Proxy ${HTTP_HOST} to ${TARGET_HOST}', 'httpdumb:${TARGET_HOST}']",
    # }),
    # ('http-raw-body', {
    #     'default': True
    # }),
])

DROP_OPTION_VALUE = object()


class _OptionAction(object):

    def converted(self, args, app_desc, key, value):
        pass

    def lint(self, args, app_desc, key, value):
        pass


class _DeprecatedAction(_OptionAction):

    def lint(self, args, app_desc, key, value):
        print("Option [%s] has been deprecated, this will likely be dropped in future releases of Galaxy." % key)


class _DeprecatedAndDroppedAction(_OptionAction):

    def converted(self, args, app_desc, key, value):
        print("Option [%s] has been deprecated and dropped. It is not included in converted configuration." % key)
        return DROP_OPTION_VALUE

    def lint(self, args, app_desc, key, value):
        print("Option [%s] has been deprecated. Option should be dropped without replacement." % key)


class _PasteAppFactoryAction(_OptionAction):

    def converted(self, args, app_desc, key, value):
        if value not in app_desc.expected_app_factories:
            raise Exception("Ending convert process - unknown paste factory encountered [%s]" % value)
        return DROP_OPTION_VALUE

    def lint(self, args, app_desc, key, value):
        if value not in app_desc.expected_app_factories:
            print("Problem - unknown paste app factory encountered [%s]" % value)


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
    'use_beaker_session': _DeprecatedAndDroppedAction(),
    'session_type': _DeprecatedAndDroppedAction(),
    'session_data_dir': _DeprecatedAndDroppedAction(),
    'session_key': _DeprecatedAndDroppedAction(),
    'session_secret': _DeprecatedAndDroppedAction(),
    'paste.app_factory': _PasteAppFactoryAction(),
    'filter-with': _HandleFilterWithAction(),
    'debug': _ProductionUnsafe(True),
    'serve_xss_vulnerable_mimetypes': _ProductionUnsafe(True),
    'use_printdebug': _ProductionUnsafe(True),
    'use_interactive': _ProductionUnsafe(True),
    'id_secret': _ProductionUnsafe('USING THE DEFAULT IS NOT SECURE!'),
    'master_api_key': _ProductionUnsafe('changethis'),
    'external_service_type_config_file': _DeprecatedAndDroppedAction(),
    'external_service_type_path': _DeprecatedAndDroppedAction(),
    'enable_sequencer_communication': _DeprecatedAndDroppedAction(),
    'run_workflow_toolform_upgrade': _DeprecatedAndDroppedAction(),
    # Next 4 were from library search which is no longer available.
    'enable_lucene_library_search': _DeprecatedAndDroppedAction(),
    'fulltext_max_size': _DeprecatedAndDroppedAction(),
    'fulltext_noindex_filetypes': _DeprecatedAndDroppedAction(),
    'fulltext_url': _DeprecatedAndDroppedAction(),
    'enable_legacy_sample_tracking_api': _DeprecatedAction(),
    'enable_new_user_preferences': _DeprecatedAndDroppedAction(),
    'force_beta_workflow_scheduled_for_collections': _DeprecatedAction(),
    'force_beta_workflow_scheduled_min_steps': _DeprecatedAction(),
    'history_local_serial_workflow_scheduling': _ProductionPerformance(),
    'allow_library_path_paste': _RenameAction("allow_path_paste"),
    'trust_ipython_notebook_conversion': _RenameAction("trust_jupyter_notebook_conversion"),
    'enable_beta_tool_command_isolation': _DeprecatedAndDroppedAction(),
    'single_user': _ProductionUnsafe(True),
    'tool_submission_burst_threads': _ProductionPerformance(),
    'tool_submission_burst_at': _ProductionPerformance(),
    'toolform_upgrade': _DeprecatedAndDroppedAction(),
}


def _app_name(self):
    return os.path.splitext(os.path.basename(self.destination))[0]


def _sample_destination(self):
    return self.destination + ".sample"


def _schema(self):
    return AppSchema(self)


App.app_name = property(_app_name)
App.sample_destination = property(_sample_destination)
App.schema = property(_schema)

OptionValue = namedtuple("OptionValue", ["name", "value", "option"])


UNKNOWN_OPTION = {
    "type": "str",
    "required": False,
    "unknown_option": True,
    "desc": "Unknown option, may want to remove or report to Galaxy team."
}

OPTION_DEFAULTS = {
    "type": "str",
    "unknown_option": False,
    "default": None,
    "desc": None,
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
        schema_path = app_desc.schema_path
        app_name = app_desc.app_name
        with open(schema_path, "r") as f:
            config_all = _ordered_load(f)
        self.raw_schema = config_all
        app_schema = config_all["mapping"][app_name]
        super(AppSchema, self).__init__(app_schema["mapping"])
        self.description = config_all.get("desc", None)

    def get_app_option(self, name):
        try:
            raw_option = self.app_schema[name]
        except KeyError:
            raw_option = UNKNOWN_OPTION
        option = OPTION_DEFAULTS.copy()
        option.update(raw_option)
        return option


GALAXY_APP = App(
    ["universe_wsgi.ini", "config/galaxy.ini"],
    "8080",
    ["galaxy.web.buildapp:app_factory"],  # TODO: Galaxy could call factory a few different things and they'd all be fine.
    "config/galaxy.yml",
    "lib/galaxy/webapps/galaxy/config_schema.yml",
    'galaxy.webapps.galaxy.buildapp:uwsgi_app()',
)
SHED_APP = App(
    ["tool_shed_wsgi.ini", "config/tool_shed.ini"],
    "9009",
    ["galaxy.webapps.tool_shed.buildapp:app_factory"],
    "config/tool_shed.yml",
    "lib/galaxy/webapps/tool_shed/config_schema.yml",
    'galaxy.webapps.tool_shed.buildapp:uwsgi_app()',
)
REPORTS_APP = App(
    ["reports_wsgi.ini", "config/reports.ini"],
    "9001",
    ["galaxy.webapps.reports.buildapp:app_factory"],
    "config/reports.yml",
    "lib/galaxy/webapps/reports/config_schema.yml",
    'galaxy.webapps.reports.buildapp:uwsgi_app()',
)
APPS = {"galaxy": GALAXY_APP, "tool_shed": SHED_APP, "reports": REPORTS_APP}


def main(argv=None):
    """Entry point for conversion process."""
    if argv is None:
        argv = sys.argv[1:]
    args = _arg_parser().parse_args(argv)
    app_name = args.app
    app_desc = APPS.get(app_name, None)
    action = args.action
    action_func = ACTIONS[action]
    action_func(args, app_desc)


def _arg_parser():
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument('action', metavar='ACTION', type=str,
                        choices=list(ACTIONS.keys()),
                        help='action to perform')
    parser.add_argument('app', metavar='APP', type=str, nargs="?",
                        help=APP_DESCRIPTION)
    parser.add_argument('--add-comments', default=False, action="store_true")
    parser.add_argument('--dry-run', default=False, action="store_true",
                        help=DRY_RUN_DESCRIPTION)
    parser.add_argument('--galaxy_root', default=".", type=str)
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
    title = "``%s``" % key
    heading = heading_level * len(title)
    rst.write("%s\n%s\n%s\n\n" % (heading, title, heading))
    option, value = _parse_option_value(option_value)
    desc = option["desc"]
    rst.write(":Description:\n")
    rst.write("\n".join(RST_DESCRIPTION_WRAPPER.wrap(desc)))
    rst.write("\n")
    type = option.get("type", None)
    default = option.get("default", "*null*")
    if default is True:
        default = "true"
    elif default is False:
        default = "false"
    rst.write(":Default: ``%s``\n" % default)
    if type:
        rst.write(":Type: %s\n" % type)
    rst.write("\n\n")


def _build_uwsgi_schema(args, app_desc):
    req = requests.get('https://raw.githubusercontent.com/unbit/uwsgi-docs/master/Options.rst')
    rst_options = req.text
    last_line = None
    current_opt = None

    options = OrderedDict({})
    option = None
    for line in rst_options.splitlines():
        line = line.strip()
        dots = "*" * len(line)
        if line and (line == dots):
            current_opt = last_line
            option = {
                'type': 'any',
            }
            options[current_opt] = option

        if line.startswith("``parser``"):
            parser = line.split(":", 1)[1].strip()
            if parser == "uwsgi_opt_set_int":
                option["type"] = "int"
            # TODO: disptch on parser...
        elif line.startswith("``help``"):
            option["desc"] = line.split(":", 1)[1]

        last_line = line
    schema = {
        "type": "map",
        "desc": "uwsgi definition, see https://uwsgi-docs.readthedocs.io/en/latest/Options.html",
        "mapping": options
    }
    path = os.path.join(args.galaxy_root, UWSGI_SCHEMA_PATH)
    contents = _ordered_dump(schema)
    _write_to_file(args, contents, path)


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
        app_items = OrderedDict()
    else:
        app_items = OrderedDict(p.items("app:main"))

    return app_items


def _lint(args, app_desc):
    path = _find_config(args, app_desc)
    if not os.path.exists(path):
        raise Exception("Expected configuration file [%s] not found." % path)
    app_items = _find_app_options(app_desc, path)
    for key, value in app_items.items():
        option_action = OPTION_ACTIONS.get(key)
        if option_action is not None:
            option_action.lint(args, app_desc, key, value)


def _validate(args, app_desc):
    path = _find_config(args, app_desc)
    # Allow empty mapping (not allowed by pykawlify)
    raw_config = _order_load_path(path)
    if raw_config.get(app_desc.app_name, None) is None:
        raw_config[app_desc.app_name] = {}
        config_p = tempfile.NamedTemporaryFile(delete=False, suffix=".yml")
        _ordered_dump(raw_config, config_p)
        config_p.flush()
        path = config_p.name

    fp = tempfile.NamedTemporaryFile(delete=False, suffix=".yml")
    _ordered_dump(app_desc.schema.raw_schema, fp)
    fp.flush()
    name = fp.name
    if Core is None:
        raise Exception("Cannot validate file, pykwalify is not installed.")
    c = Core(
        source_file=path,
        schema_files=[name],
    )
    c.validate()


class PrefixFilter(object):

    def __init__(self, name, prefix):
        self.name = name
        self.prefix = prefix


class GzipFilter(object):

    def __init__(self, name):
        self.name = name


def _run_conversion(args, app_desc):
    ini_config = _find_config(args, app_desc)
    if ini_config and not _is_ini(ini_config):
        _warn("Cannot convert YAML file %s, this option is only for ini config files." % ini_config)
        sys.exit(1)
    elif not ini_config:
        _warn("Failed to find a config to convert - exiting without changes.")
        sys.exit(1)

    p = nice_config_parser(ini_config)
    server_section = None
    filters = {}
    for section in p.sections():
        if section.startswith("server:"):
            if server_section:
                _warn(EXTRA_SERVER_MESSAGE % (server_section, section))
            else:
                server_section = section

        if section.startswith("filter:"):
            filter_name = section[len("filter:"):]
            filter_type = p.get(section, "use")
            if filter_type is None:
                MISSING_FILTER_TYPE_MESSAGE
                message = EXTRA_SERVER_MESSAGE % section
                _warn(message)
                continue

            if filter_type == "egg:PasteDeploy#prefix":
                prefix = p.get(section, "prefix")
                filters[filter_name] = PrefixFilter(filter_name, prefix)
            elif filter_type == "egg:Paste#gzip":
                filters[filter_name] = GzipFilter(filter_name)
            else:
                message = UNHANDLED_FILTER_TYPE_MESSAGE % (filter_type, section)
                _warn(message)
                continue

    if not server_section:
        _warn("No server section found, using default uwsgi server definition.")
        server_config = OrderedDict()
    else:
        server_config = OrderedDict(p.items(server_section))

    app_items = _find_app_options_from_config_parser(p)
    applied_filters = []
    if filters:
        for key, value in app_items.items():
            if key == "filter-with":
                if value in filters:
                    applied_filters.append(filters[value])
                else:
                    _warn("Unknown filter found [%s], exiting..." % value)
                    sys.exit(1)

    uwsgi_dict = _server_paste_to_uwsgi(app_desc, server_config, applied_filters)

    app_dict = OrderedDict({})
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
    _write_section(args, f, "uwsgi", uwsgi_dict, uwsgi_hack=True)
    _write_section(args, f, app_desc.app_name, app_dict)
    destination = os.path.join(args.galaxy_root, app_desc.destination)
    _replace_file(args, f, app_desc, ini_config, destination)


def _is_ini(path):
    return path.endswith(".ini") or path.endswith(".ini.sample")


def _replace_file(args, f, app_desc, from_path, to_path):
    _write_to_file(args, f, to_path)
    backup_path = "%s.backup" % from_path
    print("Moving [%s] to [%s]" % (from_path, backup_path))
    if args.dry_run:
        print("... skipping because --dry-run is enabled.")
    else:
        shutil.move(from_path, backup_path)


def _build_sample_yaml(args, app_desc):
    schema = app_desc.schema
    f = StringIO()
    for key, value in UWSGI_OPTIONS.items():
        for field in ["desc", "default"]:
            if field not in value:
                continue
            field_value = value[field]
            if not isinstance(field_value, six.string_types):
                continue

            new_field_value = string.Template(field_value).safe_substitute(**{
                'default_port': str(app_desc.default_port),
                'app_name': app_desc.app_name,
                'uwsgi_module': app_desc.uwsgi_module,
            })
            value[field] = new_field_value
    description = getattr(schema, "description", None)
    if description:
        description = description.lstrip()
        as_comment = "\n".join(["# %s" % l for l in description.split("\n")]) + "\n"
        f.write(as_comment)
    _write_sample_section(args, f, 'uwsgi', Schema(UWSGI_OPTIONS), as_comment=False, uwsgi_hack=True)
    _write_sample_section(args, f, app_desc.app_name, schema)
    destination = os.path.join(args.galaxy_root, app_desc.sample_destination)
    _write_to_file(args, f, destination)


def _write_to_file(args, f, path):
    dry_run = args.dry_run
    if hasattr(f, "getvalue"):
        contents = f.getvalue()
    else:
        contents = f
    contents_indented = "\n".join([" |%s" % l for l in contents.splitlines()])
    print("Writing the file contents:\n%s\nto %s" % (contents_indented, path))
    if dry_run:
        print("... skipping because --dry-run is enabled.")
    else:
        safe_makedirs(os.path.dirname(path))
        with open(path, "w") as to_f:
            to_f.write(contents)


def _order_load_path(path):
    """Load (with ``_ordered_load``) on specified path (a YAML file)."""
    with open(path, "r") as f:
        # Allow empty mapping (not allowed by pykawlify)
        raw_config = _ordered_load(f)
        return raw_config


def _write_sample_section(args, f, section_header, schema, as_comment=True, uwsgi_hack=False):
    _write_header(f, section_header)
    for key, value in schema.app_schema.items():
        default = None if "default" not in value else value["default"]
        option = schema.get_app_option(key)
        option_value = OptionValue(key, default, option)
        # support uWSGI "dumb yaml parser" (unbit/uwsgi#863)
        key = option.get('key', key)
        _write_option(args, f, key, option_value, as_comment=as_comment, uwsgi_hack=uwsgi_hack)


def _write_section(args, f, section_header, section_dict, uwsgi_hack=False):
    _write_header(f, section_header)
    for key, option_value in section_dict.items():
        _write_option(args, f, key, option_value, uwsgi_hack=uwsgi_hack)


def _write_header(f, section_header):
    f.write("%s:\n\n" % section_header)


def _write_option(args, f, key, option_value, as_comment=False, uwsgi_hack=False):
    option, value = _parse_option_value(option_value)
    desc = option["desc"]
    comment = ""
    if desc and args.add_comments:
        comment = "\n".join(YAML_COMMENT_WRAPPER.wrap(desc))
        comment += "\n"
    as_comment_str = "#" if as_comment else ""
    if uwsgi_hack:
        if option.get("type", "str") == "bool":
            value = str(value).lower()
        key_val_str = "%s: %s" % (key, value)
    else:
        key_val_str = yaml.dump({key: value}, width=float("inf")).lstrip("{").rstrip("\n}")
    lines = "%s%s%s" % (comment, as_comment_str, key_val_str)
    lines_idented = "\n".join([("  %s" % l) for l in lines.split("\n")])
    f.write("%s\n\n" % lines_idented)


def _parse_option_value(option_value):
    if isinstance(option_value, OptionValue):
        option = option_value.option
        value = option_value.value
        # Hack to get nicer YAML values during conversion
        if option.get("type", "str") == "bool":
            value = str(value).lower() == "true"
        elif option.get("type", "str") == "int":
            value = int(value)
    else:
        value = option_value
        option = OPTION_DEFAULTS
    return option, value


def _server_paste_to_uwsgi(app_desc, server_config, applied_filters):
    uwsgi_dict = OrderedDict()
    port = server_config.get("port", app_desc.default_port)
    host = server_config.get("host", "127.0.0.1")

    if server_config.get("use", "egg:Paste#http") != "egg:Paste#http":
        raise Exception("Unhandled paste server 'use' value [%s], file must be manually migrate.")

    uwsgi_dict["http"] = "%s:%s" % (host, port)
    # default changing from 10 to 8
    uwsgi_dict["threads"] = int(server_config.get("threadpool_workers", 8))
    # required for static...
    uwsgi_dict["http-raw-body"] = True
    uwsgi_dict["offload-threads"] = 8

    # Handle paste filters during conversion.
    prefix = None
    for applied_filter in applied_filters:
        if isinstance(applied_filter, PrefixFilter):
            prefix = applied_filter.prefix
            break
        elif isinstance(applied_filter, GzipFilter):
            uwsgi_dict["http-auto-gzip"] = True

    if prefix:
        uwsgi_dict["mount"] = "%s=%s" % (prefix, app_desc.uwsgi_module)
        uwsgi_dict["manage-script-name"] = True
    else:
        uwsgi_dict["module"] = app_desc.uwsgi_module
    return uwsgi_dict


def _warn(message):
    print("WARNING: %s" % message)


def _ordered_load(stream):

    class OrderedLoader(yaml.Loader):

        def __init__(self, stream):
            self._root = os.path.split(stream.name)[0]
            super(OrderedLoader, self).__init__(stream)

        def include(self, node):
            filename = os.path.join(self._root, self.construct_scalar(node))
            with open(filename, 'r') as f:
                return yaml.load(f, OrderedLoader)

    def construct_mapping(loader, node):
        loader.flatten_mapping(node)
        return OrderedDict(loader.construct_pairs(node))

    OrderedLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        construct_mapping)
    OrderedLoader.add_constructor('!include', OrderedLoader.include)

    return yaml.load(stream, OrderedLoader)


def _ordered_dump(data, stream=None, Dumper=yaml.Dumper, **kwds):
    class OrderedDumper(Dumper):
        pass

    def _dict_representer(dumper, data):
        return dumper.represent_mapping(
            yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
            list(data.items()))
    OrderedDumper.add_representer(OrderedDict, _dict_representer)
    return yaml.dump(data, stream, OrderedDumper, **kwds)


ACTIONS = {
    "convert": _run_conversion,
    "build_sample_yaml": _build_sample_yaml,
    "validate": _validate,
    "lint": _lint,
    "build_uwsgi_yaml": _build_uwsgi_schema,
    "build_rst": _to_rst,
}


if __name__ == '__main__':
    main()
