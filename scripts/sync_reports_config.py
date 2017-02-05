from ConfigParser import ConfigParser
from sys import argv

REPLACE_PROPERTIES = ["file_path", "database_connection", "new_file_path"]
MAIN_SECTION = "app:main"


def sync():
    # Add or replace the relevant properites from galaxy.ini
    # into reports.ini
    reports_config_file = "config/reports.ini"
    if len(argv) > 1:
        reports_config_file = argv[1]

    universe_config_file = "config/galaxy.ini"
    if len(argv) > 2:
        universe_config_file = argv[2]

    parser = ConfigParser()
    parser.read(universe_config_file)

    with open(reports_config_file, "r") as f:
        reports_config_lines = f.readlines()

    replaced_properties = set([])
    with open(reports_config_file, "w") as f:
        # Write all properties from reports config replacing as
        # needed.
        for reports_config_line in reports_config_lines:
            (line, replaced_property) = get_synced_line(reports_config_line, parser)
            if replaced_property:
                replaced_properties.add(replaced_property)
            f.write(line)

        # If any properties appear in universe config and not in
        # reports write these as well.
        for replacement_property in REPLACE_PROPERTIES:
            if parser.has_option(MAIN_SECTION, replacement_property) and \
                    not (replacement_property in replaced_properties):
                f.write(get_universe_line(replacement_property, parser))


def get_synced_line(reports_line, universe_config):
    # Cycle through properties to replace and perform replacement on
    # this line if needed.
    synced_line = reports_line
    replaced_property = None
    for replacement_property in REPLACE_PROPERTIES:
        if reports_line.startswith(replacement_property) and \
                universe_config.has_option(MAIN_SECTION, replacement_property):
            synced_line = get_universe_line(replacement_property, universe_config)
            replaced_property = replacement_property
            break
    return (synced_line, replaced_property)


def get_universe_line(property_name, universe_config):
    return "%s=%s\n" % (property_name, universe_config.get(MAIN_SECTION, property_name))


if __name__ == '__main__':
    sync()
