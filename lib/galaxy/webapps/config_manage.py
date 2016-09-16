from __future__ import absolute_import
from __future__ import print_function

import argparse
from collections import namedtuple
from collections import OrderedDict
import copy
import os
import shutil
import string
import sys
import tempfile
from textwrap import TextWrapper
import urllib2

import six
from six import StringIO

import yaml

try:
    from pykwalify.core import Core
except ImportError:
    Core = None


from galaxy.util.properties import nice_config_parser

DESCRIPTION = "Convert configuration files."

APP_DESCRIPTION = """Application to target for operation (i.e. galaxy, tool_shed, or reports))"""
DRY_RUN_DESCRIPTION = """If this action modifies files, just print what would be the result and continue."""
UNKNOWN_OPTION_MESSAGE = "Option [%s] not found in schema - either it is invalid or the Galaxy team hasn't documented it. If invalid, you should manually remove it. If the option is valid but undocumented, please file an issue with the Galaxy team."
USING_SAMPLE_MESSAGE = "Path [%s] not a file, using sample."
YAML_COMMENT_WRAPPER = TextWrapper(initial_indent="# ", subsequent_indent="# ")
RST_DESCRIPTION_WRAPPER = TextWrapper(initial_indent="    ", subsequent_indent="    ")
UWSGI_SCHEMA_PATH = "lib/galaxy/webapps/uwsgi_schema.yml"

App = namedtuple(
    "App",
    ["config_paths", "default_port", "expected_app_factories", "destination", "schema_path", "uwsgi_module"]
)

UWSGI_OPTIONS = OrderedDict([
    ('http', {
        'desc': """The address and port on which to listen.  By default, only listen to localhost ($app_name will not be accessible over the network).  Use '0.0.0.0' to listen on all available network interfaces.""",
        'default': '127.0.0.1:$default_port',
        'type': 'str',
    }),
    ('threads', {
        'default': 8,
        'type': 'int',
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
    ('http-raw-body', {
        'default': 'True'
    }),
    ('offload-threads', {
        'default': '8',
    }),
    ('module', {
        'default': '$uwsgi_module',
        'type': 'str',
    })
])


def _app_name(self):
    return os.path.splitext(os.path.basename(self.destination))[0]


def _sample_destination(self):
    return self.destination + ".sample"


def _schema(self):
    return AppSchema(self)


App.app_name = property(_app_name)
App.sample_destination = property(_sample_destination)
App.schema = property(_schema)

OptionValue = namedtuple("OptionValue", ["name", "value", "option"] )


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
        argv = sys.argv
    args = _arg_parser().parse_args(argv)
    app_name = args.app
    app_desc = APPS.get(app_name, None)
    action = args.action
    if action == "convert":
        _run_conversion(args, app_desc)
    elif action == "build_sample_yaml":
        _build_sample_yaml(args, app_desc)
    elif action == "validate":
        _validate(args, app_desc)
    elif action == "build_uwsgi_yaml":
        _build_uwsgi_schema(args, app_desc)
    elif action == "build_rst":
        _to_rst(args, app_desc)
    else:
        raise Exception("Unknown config action [%s]" % action)


def _arg_parser():
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument('action', metavar='ACTION', type=str,
                        help='action (convert, build_sample_yaml, validate))')
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
    rst.write(":Default: %s\n" % default)
    if type:
        rst.write(":Type: %s\n" % type)
    rst.write("\n\n")


def _build_uwsgi_schema(args, app_desc):
    req = urllib2.Request('https://raw.githubusercontent.com/unbit/uwsgi-docs/master/Options.rst')
    response = urllib2.urlopen(req)
    rst_options = response.read()
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
        "desc": "uwsgi definition, see http://uwsgi-docs.readthedocs.io/en/latest/Options.html",
        "mapping": options
    }
    path = os.path.join(args.galaxy_root, UWSGI_SCHEMA_PATH)
    with open(path, "w") as f:
        _ordered_dump(schema, f)


def _validate(args, app_desc):
    path = os.path.join(args.galaxy_root, app_desc.destination)
    if not os.path.exists(path):
        _warn(USING_SAMPLE_MESSAGE % path)
        path = os.path.join(args.galaxy_root, app_desc.sample_destination)
    with open(path, "r") as f:
        # Allow empty mapping (not allowed by pykawlify)
        raw_config = _ordered_load(f)
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


def _run_conversion(args, app_desc):
    ini_config = None
    for possible_ini_config_rel in app_desc.config_paths:
        possible_ini_config = os.path.join(args.galaxy_root, possible_ini_config_rel)
        if os.path.exists(possible_ini_config):
            ini_config = possible_ini_config

    if not ini_config:
        _warn("Failed to find a config to convert - exiting without changes.")
        sys.exit(1)

    p = nice_config_parser(ini_config)

    server_section = None
    app_main_found = False

    for section in p.sections():
        if section.startswith("server:"):
            if server_section:
                message = "Additional server section after [%s] encountered [%s], will be ignored."
                _warn(message % (server_section, section))
            else:
                server_section = section
        elif section == "app:main":
            app_main_found = True

    if not server_section:
        _warn("No server section found, using default uwsgi server definition.")
        server_config = OrderedDict()
    else:
        server_config = OrderedDict(p.items(server_section))

    uwsgi_dict = _server_paste_to_uwsgi(app_desc, server_config)

    if not app_main_found:
        _warn("No app:main section found, using application defaults throughout.")
        app_items = OrderedDict()
    else:
        app_items = OrderedDict(p.items("app:main"))

    app_dict = OrderedDict({})
    schema = app_desc.schema
    for key, value in app_items.items():
        if key == "paste.app_factory":
            assert value in app_desc.expected_app_factories
            continue

        option = schema.get_app_option(key)
        if option["unknown_option"]:
            _warn(UNKNOWN_OPTION_MESSAGE % key)

        option_value = OptionValue(key, value, option)
        app_dict[key] = option_value

    f = StringIO()
    _write_section(args, f, "uwsgi", uwsgi_dict)
    _write_section(args, f, app_desc.app_name, app_dict)
    destination = os.path.join(args.galaxy_root, app_desc.destination)
    _replace_file(args, f, app_desc, ini_config, destination)


def _replace_file(args, f, app_desc, from_path, to_path):
    _write_buffer_to_file(args, f, to_path)
    backup_path = "%s.backup" % from_path
    print("Moving [%s] to [%s]" % (from_path, backup_path))
    if args.dry_run:
        print("... skipping because --dry-run is enabled.")
    else:
        shutil.move(from_path, backup_path)


def _build_sample_yaml(args, app_desc):
    schema = app_desc.schema
    f = StringIO()
    options = copy.deepcopy(UWSGI_OPTIONS)
    for key, value in options.items():
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
    _write_sample_section(args, f, 'uwsgi', Schema(options), as_comment=False)
    _write_sample_section(args, f, app_desc.app_name, schema)
    destination = os.path.join(args.galaxy_root, app_desc.sample_destination)
    _write_buffer_to_file(args, f, destination)


def _write_buffer_to_file(args, f, path):
    dry_run = args.dry_run
    contents = f.getvalue()
    contents_indented = "\n".join([" |%s" % l for l in contents.splitlines()])
    print("Writing the file contents:\n%s\nto %s" % (contents_indented, path))
    if dry_run:
        print("... skipping because --dry-run is enabled.")
    else:
        with open(path, "w") as to_f:
            to_f.write(contents)


def _write_sample_section(args, f, section_header, schema, as_comment=True):
    _write_header(f, section_header)
    for key, value in schema.app_schema.items():
        default = None if "default" not in value else value["default"]
        option = schema.get_app_option(key)
        option_value = OptionValue(key, default, option)
        _write_option(args, f, key, option_value, as_comment=as_comment)


def _write_section(args, f, section_header, section_dict):
    _write_header(f, section_header)
    for key, option_value in section_dict.items():
        _write_option(args, f, key, option_value)


def _write_header(f, section_header):
    f.write("%s:\n\n" % section_header)


def _write_option(args, f, key, option_value, as_comment=False):
    option, value = _parse_option_value(option_value)
    desc = option["desc"]
    comment = ""
    if desc and args.add_comments:
        comment = "\n".join(YAML_COMMENT_WRAPPER.wrap(desc))
        comment += "\n"
    as_comment_str = "#" if as_comment else ""
    key_val_str = yaml.dump({key: value}).lstrip("{").rstrip("\n}")
    lines = "%s%s%s" % (comment, as_comment_str, key_val_str)
    lines_idented = "\n".join([("  %s" % l) for l in lines.split("\n")])
    f.write("%s\n\n" % lines_idented)


def _parse_option_value(option_value):
    if isinstance(option_value, OptionValue):
        option = option_value.option
        value = option_value.value
    else:
        value = option_value
        option = OPTION_DEFAULTS
    return option, value


def _server_paste_to_uwsgi(app_desc, server_config):
    uwsgi_dict = OrderedDict()
    port = server_config.get("port", app_desc.default_port)
    host = server_config.get("host", "127.0.0.1")

    if server_config.get("use", "egg:Paste#http") != "egg:Paste#http":
        raise Exception("Unhandled paste server 'use' value [%s], file must be manually migrate.")

    uwsgi_dict["http"] = "%s:%s" % (host, port)
    # default changing from 10 to 8
    uwsgi_dict["threads"] = server_config.get("threadpool_workers", "8")
    # required for static...
    uwsgi_dict["http-raw-body"] = True
    uwsgi_dict["offload-threads"] = 8
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
            data.items())
    OrderedDumper.add_representer(OrderedDict, _dict_representer)
    return yaml.dump(data, stream, OrderedDumper, **kwds)


if __name__ == '__main__':
    main()
