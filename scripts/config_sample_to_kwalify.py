import sys


def main():
    """Entry point for conversion procedure."""
    found_app_main = False
    current_section_desc = []
    current_section_options = []
    try:
        sample = sys.argv[1]
    except KeyError:
        sample = "config/galaxy.ini.sample"

    for line in open(sample):
        is_app_main = line.startswith("[app:main]")
        if not found_app_main and not is_app_main:
            continue
        if is_app_main:
            found_app_main = True
            continue

        line = line.strip()
        if not line.startswith("#"):
            for section_option in current_section_options:
                _dump_option(section_option, current_section_desc)
            current_section_desc = []
            current_section_options = []
        if line.startswith("[galaxy_amqp]"):
            break

        if line.startswith("# ") or "#" == line:
            current_section_desc.append(line[2:])
        elif line.startswith("#"):
            current_section_options.append(line)


def _dump_option(option, current_section_desc):
    def print_line(line):
        print((" " * 6) + line)

    if "=" not in option:
        print(option)
    key, default = (s.strip() for s in option.split("=", 1))
    key = key[1:]  # strip #
    if default.strip().lower() in ["true", "false"]:
        default = default.lower()
        type = "bool"
    elif default.isdigit():
        type = "int"
    else:
        try:
            float(default)
            type = "float"
        except ValueError:
            type = "str"
    if default == "None":
        default = None
    print_line("%s:" % key)
    print_line("  type: %s" % type)
    if default is not None:
        print_line("  default: %s" % default)
    # print_line("  required: false")
    print_line("  desc: |")
    for line in current_section_desc:
        print_line("    %s" % line)
    print_line("")


if __name__ == "__main__":
    main()
