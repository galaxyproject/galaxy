from __future__ import print_function

import argparse
from collections import namedtuple
from collections import OrderedDict
import os
import sys
import tempfile
from textwrap import TextWrapper
import urllib2

from six.moves.configparser import SafeConfigParser
from six import StringIO

import yaml

try:
    from pykwalify.core import Core
except ImportError:
    Core = None

DESCRIPTION = "Convert configuration files."
UNKNOWN_OPTION_MESSAGE = "Option [%s] not found in schema - either it is invalid or the Galaxy team hasn't documented it. If invalid, you should manually remove it. If the option is valid but undocumented, please file an issue with the Galaxy team."
YAML_COMMENT_WRAPPER = TextWrapper(initial_indent="# ", subsequent_indent="# ")

App = namedtuple(
    "App",
    ["config_paths", "default_port", "expected_app_factories", "destination", "schema_path"]
)


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


class AppSchema(object):

    def __init__(self, app_desc):
        schema_path = app_desc.schema_path
        app_name = app_desc.app_name
        with open(schema_path, "r") as f:
            config_all = _ordered_load(f)
        self.raw_schema = config_all
        app_schema = config_all["mapping"][app_name]
        self.app_schema = app_schema["mapping"]

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
    None,  # TODO
)
SHED_APP = App(
    ["tool_shed_wsgi.ini", "config/tool_shed.ini"],
    "9009",
    ["galaxy.webapps.tool_shed.buildapp:app_factory"],
    "config/tool_shed.yml",
    "lib/galaxy/webapps/tool_shed/config_schema.yml",  # TODO
)
REPORTS_APP = App(
    ["reports_wsgi.ini", "config/reports.ini"],
    "9001",
    ["galaxy.webapps.reports.buildapp:app_factory"],
    "config/reports.yml",
    None,  # TODO
)
APPS = {"galaxy": GALAXY_APP, "tool_shed": SHED_APP, "reports": REPORTS_APP}


def main():
    """Entry point for conversion process."""
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument('action', metavar='ACTION', type=str,
                        help='action (convert, build_sample_yaml, validate))')
    parser.add_argument('app', metavar='APP', type=str, nargs="?",
                        help='app (galaxy, tool_shed, or reports))')
    parser.add_argument('--add_comments', default=False, action="store_true")
    args = parser.parse_args()
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
    else:
        raise Exception("Unknown config action [%s]" % action)


def _build_uwsgi_schema(args, app_desc):
    req = urllib2.Request('https://raw.githubusercontent.com/unbit/uwsgi-docs/master/Options.rst')
    response = urllib2.urlopen(req)
    rst_options = response.read()
    last_line = None
    current_opt = None
    current_parser = None
    current_help = None
    for line in rst_options.splitlines():
        line = line.strip()
        dots = "*" * len(line)
        if line and (line == dots):
            current_opt = last_line
            print("New opt %s" % current_opt)
            if line.startswith("``parser``"):
                current_parser = line.split(":", 1)[1]
            elif line.startswith("``help``"):
                current_help = line.split(":", 1)[1]
        last_line = line



def _validate(args, app_desc):
    path = app_desc.destination
    if not os.path.exists(path):
        _warn("Path [%s] not a file, using sample.")
        path = app_desc.sample_destination
    fp = tempfile.NamedTemporaryFile(delete=False, suffix=".yml")
    _ordered_dump(app_desc.schema.raw_schema, fp)
    print(_ordered_dump(app_desc.schema.raw_schema))
    fp.flush()
    name = fp.name
    c = Core(
        source_file=path,
        schema_files=[name],
    )
    c.validate()


def _run_conversion(args, app_desc):
    ini_config = None
    for possible_ini_config in app_desc.config_paths:
        if os.path.exists(possible_ini_config):
            ini_config = possible_ini_config

    if not ini_config:
        _warn("Failed to find a config to convert - exiting without changes.")
        sys.exit(1)

    p = SafeConfigParser()
    p.read(ini_config)

    server_section = None
    app_main_found = False

    for section in p.sections():
        if section.startswith("server:"):
            if server_section:
                message = "Additional sever section after [%s] encountered [%s], will be ignored."
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
    print(f.getvalue())


def _build_sample_yaml(args, app_desc):
    schema = app_desc.schema
    f = StringIO()
    _write_sample_section(args, f, app_desc.app_name, schema)
    print(f.getvalue())


def _write_sample_section(args, f, section_header, schema):
    _write_header(f, section_header)
    for key, value in schema.app_schema.items():
        default = value["default"]
        option = schema.get_app_option(key)
        option_value = OptionValue(key, default, option)
        _write_option(args, f, key, option_value, as_comment=True)


def _write_section(args, f, section_header, section_dict):
    _write_header(f, section_header)
    for key, option_value in section_dict.items():
        _write_option(args, f, key, option_value)


def _write_header(f, section_header):
    f.write("%s:\n\n" % section_header)


def _write_option(args, f, key, option_value, as_comment=False):
    if isinstance(option_value, OptionValue):
        option = option_value.option
        value = option_value.value
    else:
        value = option_value
        option = OPTION_DEFAULTS
    desc = option["desc"]
    comment = ""
    if desc and args.add_comments:
        comment = "\n".join(YAML_COMMENT_WRAPPER.wrap(desc))
        comment += "\n"
    as_comment_str = "#" if as_comment else ""
    lines = "%s%s%s: %s" % (comment, as_comment_str, key, value)
    lines_idented = "\n".join([("  %s" % l) for l in lines.split("\n")])
    f.write("%s\n\n" % lines_idented)


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
