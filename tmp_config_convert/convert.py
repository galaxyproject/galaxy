
import string

HEADER = """
type: map
desc: |
  Galaxy is configured by default to be usable in a single-user development
  environment.  To tune the application for a multi-user production
  environment, see the documentation at:
  
   http://usegalaxy.org/production
  
  Throughout this sample configuration file, except where stated otherwise,
  uncommented values override the default if left unset, whereas commented
  values are set to the default value.  Relative paths are relative to the root
  Galaxy directory.
  
  Examples of many of these options are explained in more detail in the Galaxy
  Community Hub.
 
    https://galaxyproject.org/admin/config
  
  Config hackers are encouraged to check there before asking for help.
mapping:
  uwsgi: !include uwsgi_schema.yml
  galaxy:
    type: map
    required: true
    mapping:
"""

OPTION_TEMPLATE = string.Template("""      $name:
        type: $type_guess
$default_line        required: false
        desc: |
$desc""")

print(HEADER)
with open("galaxy.ini.sample", "r") as f:
    lines = f.readlines()

    last_block = ""
    for line in lines:
        line = line.rstrip("\n")
        if not line.strip():
            last_block = ""
            continue
        if line.startswith("# ") or line == "#":
            last_block += line.lstrip("#") + "\n"
            continue
        elif line.startswith("#"):
            assert "=" in line, line
            name, value = line.split("=", 1)
            name = name.lstrip("#").strip()
            default = value.strip()
            desc = "\n".join(["         %s" % l for l in last_block.split("\n")])
            type_guess = "str"
            if default:
                # Python -> YAML
                if default == "None":
                    default = "null"
                if name.endswith("_boost"):
                    # boost search modifiers - only floats?
                    type_guess = "float"
                elif default.isdigit():
                    type_guess = "int"
                elif default.lower() in ["true", "false"]:
                    type_guess = "bool"
                    default = default.lower()
                default_line = "        default: %s\n" % default
            else:
                default_line = ""

            print(OPTION_TEMPLATE.safe_substitute(
                name=name,
                default_line=default_line,
                desc=desc,
                type_guess=type_guess,
            ))
        else:
            assert False, "[%s]" % line
