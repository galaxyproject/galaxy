#!/usr/bin/env python
import argparse
import shutil
from datetime import datetime

from lxml import etree

desc = """
Fix shed_data_manager_conf.xml

Modifies the guid and version attribute of data_manager tags:

- the version in the guid (text after the last slash) is replaced
  by the data manager tool version
- the version attribute is set to the data manager tool version

By default only data managers with duplicated guid are modified
and version attributes are not added if absent.

A copy of the original file with a time stamp appended to the name
is created.

Note, if there are versions of the data manager tool that have the
same version there will still be DMs with duplicated guids. These
need to be corrected manually.
"""

parser = argparse.ArgumentParser(description=desc)
parser.add_argument(
    "shed_data_manager_conf",
    metavar="CONFIG_FILE",
    type=str,
    default="config/shed_data_manager_conf.xml",
    help="an integer for the accumulator",
)
parser.add_argument(
    "--all-entries", action="store_true", help="modify all entries (default only those with duplicated guid)"
)
parser.add_argument("--add-version", action="store_true", help="also add version attribute if absent")
parser.add_argument("--dry-run", action="store_true", help="do not write resulting config file")
args = parser.parse_args()

with open(args.shed_data_manager_conf) as fh:
    tree = etree.parse(args.shed_data_manager_conf)
root = tree.getroot()

guid_mapping = dict()
for dm in root.iter("data_manager"):
    guid = dm.attrib["guid"]
    if guid not in guid_mapping:
        guid_mapping[guid] = [dm]
    else:
        guid_mapping[guid].append(dm)

for guid in guid_mapping:
    if len(guid_mapping[guid]) > 1:
        print(f"{guid} found {len(guid_mapping[guid])}x")
    elif not args.all_entries:
        continue

    for dm in guid_mapping[guid]:
        tool_version = dm.find("./tool/version")
        tool_version = tool_version.text

        new_guid = f"{guid[:guid.rfind('/')]}/{tool_version}"
        dm.attrib["guid"] = new_guid
        print(f"changing guid: {guid} -> {new_guid}")
        if "version" in dm.attrib:
            print(f"changing version: {dm.attrib['version']} -> {tool_version}")
            dm.attrib["version"] = tool_version
        elif args.add_version:
            print(f"adding version: {tool_version}")
            dm.attrib["version"] = tool_version

if not args.dry_run:
    nfn = args.shed_data_manager_conf + datetime.now().isoformat()
    print(f"save copy at {nfn}")
    shutil.copyfile(args.shed_data_manager_conf, nfn)
    print(f"saving {args.shed_data_manager_conf}")
    tree.write(args.shed_data_manager_conf)
