#!/usr/bin/env python3
#
# Reorganize tool data to the layout described in https://github.com/galaxyproject/galaxy/discussions/19013
#
import argparse
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
from collections import namedtuple
from enum import Enum
from xml.etree import ElementTree


class PathType(Enum):
    # path column is path to a single file
    FILE = 1
    # path column is path to a directory
    DIRECTORY = 2
    # path column is path to a file prefix in a directory
    DIRECTORY_PREFIX = 3

PATH_TEMPLATES = {
    "all_fasta": "{tool_data_path}/genomes/{dbkey}/seq/{value}.fa",
    "__dbkeys__": "{tool_data_path}/genomes/{dbkey}/len/{value}.len",
    "fasta_indexes": "{tool_data_path}/genomes/{dbkey}/sam_fasta_index/v1/{value}/{value}.fa",
    "bowtie_indexes": "{tool_data_path}/genomes/{dbkey}/bowtie_index/v1/{value}/{value}.fa",
    "bowtie2_indexes": "{tool_data_path}/genomes/{dbkey}/bowtie_index/v2/{value}/{value}.fa",
    "bwa_mem_indexes": "{tool_data_path}/genomes/{dbkey}/bwa_mem_index/v1/{value}/{value}.fa",
    "bwa_mem2_indexes": "{tool_data_path}/genomes/{dbkey}/bwa_mem_index/v2/{value}/{value}.fa",
    "hisat2_indexes": "{tool_data_path}/genomes/{dbkey}/hisat_index/v2/{value}/{value}.fa",
    "rnastar_index2x_versioned": "{tool_data_path}/genomes/{dbkey}/rnastar_index/v{version}/{value}",

}

PATH_TYPES = {
    "all_fasta": PathType.FILE,
    "__dbkeys__": PathType.FILE,
    "fasta_indexes": PathType.DIRECTORY_PREFIX,
    "bowtie_indexes": PathType.DIRECTORY_PREFIX,
    "bowtie2_indexes": PathType.DIRECTORY_PREFIX,
    "bwa_mem_indexes": PathType.DIRECTORY_PREFIX,
    "bwa_mem2_indexes": PathType.DIRECTORY_PREFIX,
    "hisat2_indexes": PathType.DIRECTORY_PREFIX,
    "rnastar_index2x_versioned": PathType.DIRECTORY,
}

class Color:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"
    BLINK = "\033[5m"
    REVERSE = "\033[7m"
    HIDDEN = "\033[8m"
    
    # Foreground colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    
    # Bright foreground colors
    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"
    
    # Background colors
    BG_BLACK = "\033[40m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"
    BG_WHITE = "\033[47m"
    
    # Bright background colors
    BG_BRIGHT_BLACK = "\033[100m"
    BG_BRIGHT_RED = "\033[101m"
    BG_BRIGHT_GREEN = "\033[102m"
    BG_BRIGHT_YELLOW = "\033[103m"
    BG_BRIGHT_BLUE = "\033[104m"
    BG_BRIGHT_MAGENTA = "\033[105m"
    BG_BRIGHT_CYAN = "\033[106m"
    BG_BRIGHT_WHITE = "\033[107m"
    
    @staticmethod
    def sprint(text, color, effect=None):
        effect = effect or ''
        return f"{color}{effect}{text}{Color.RESET}"

    @staticmethod
    def print(text, color, effect=None):
        print(Color.sprint(text, color, effect=effect))


class LocFile:
    def __init__(self, path, table, comment_char):
        self.file = open(path, "rt")
        self.table = table
        self.comment_char = comment_char
        self.line_re = re.compile(f'^([^{comment_char}]*)')

    def __iter__(self):
        for line in self.file:
            line = line.strip()
            match = re.match(self.line_re, line)
            if match and match.group(0).strip():
                yield self.table(*match.group(0).strip().split("\t"))


class DataTable:
    @classmethod
    def from_elem(cls, elem, tool_data_path=None):
        name = elem.attrib["name"]
        comment_char = elem.attrib.get("comment_char", "#")
        columns = [c.strip() for c in elem.find("columns").text.split(",")]
        loc_file_path = elem.find("file").attrib["path"].strip()
        return cls(name, columns, loc_file_path, comment_char, tool_data_path=tool_data_path)

    def __init__(self, name, columns, loc_file_path, comment_char, tool_data_path=None):
        self.name = name
        self.columns = columns
        self.loc_file_path = loc_file_path
        self.comment_char = comment_char
        self.table = namedtuple(name, columns)
        self._tool_data_path = tool_data_path
        self.loc_file = LocFile(loc_file_path, self.table, comment_char)
        self._initialize_new_loc_file()

    def _initialize_new_loc_file(self):
        fd, self.new_loc_file_path = tempfile.mkstemp(
            suffix=".reorganize_tool_data.loc",
            prefix=f"{self.name}.",
            dir=os.path.dirname(self.loc_file_path),
            text=True
        )
        self.new_loc_file = os.fdopen(fd, mode="wt")

    @property
    def path_type(self):
        return PATH_TYPES[self.name]

    @property
    def tool_data_path(self):
        assert self._tool_data_path is not None
        return self._tool_data_path

    def _table_path(self, entry):
        template_dict = {"tool_data_path": self.tool_data_path}
        template_dict.update(entry._asdict())
        return PATH_TEMPLATES[self.name].format(**template_dict)

    def _source_path(self, entry):
        if self.path_type in (PathType.FILE, PathType.DIRECTORY):
            return entry.path
        elif self.path_type == PathType.DIRECTORY_PREFIX:
            return os.path.dirname(entry.path)
        else:
            raise NotImplementedError(self.path_type)

    def _dest_path(self, entry):
        if self.path_type in (PathType.FILE, PathType.DIRECTORY):
            return self._table_path(entry)
        elif self.path_type == PathType.DIRECTORY_PREFIX:
            return os.path.dirname(self._table_path(entry))
        else:
            raise NotImplementedError(self.path_type)

    def _map_links(self, entry):
        # only considers links in the first level dir
        source = self._source_path(entry)
        dest = self._dest_path(entry)
        link_map = []
        if self.path_type == PathType.FILE:
            if os.path.islink(source):
                target = os.path.normpath(os.path.join(os.path.dirname(source), os.readlink(source)))
                link_map.append((dest, os.path.relpath(target, start=os.path.dirname(dest))))
        elif self.path_type in (PathType.DIRECTORY, PathType.DIRECTORY_PREFIX):
            for dirent in os.scandir(source):
                if dirent.is_symlink():
                    target = os.path.normpath(os.path.join(source, os.readlink(dirent.path)))
                    link_map.append((os.path.join(dest, dirent.name), os.path.relpath(target, start=dest)))
        else:
            raise NotImplementedError(self.path_type)
        return link_map

    def _write_entry_to_loc(self, entry, path=None):
        if path:
            new_entry_dict = entry._asdict()
            new_entry_dict.update({"path": path})
            new_entry = self.table(**new_entry_dict)
        else:
            new_entry = entry
        new_entry_str = "\t".join(new_entry)
        self.new_loc_file.write(f"{new_entry_str}\n")

    def reorganize(self, commit=False):
        changed = False
        for entry in self.loc_file:
            try:
                dest_path = self._table_path(entry)
                if dest_path != entry.path:
                    link_map = self._map_links(entry)
                    source = self._source_path(entry)
                    dest = self._dest_path(entry)
                    assert os.path.lexists(source) and os.path.exists(source), Color.sprint(f"ERROR: source path does not exist: {source}", Color.RED, effect=Color.BOLD)
                    assert not os.path.exists(dest), Color.sprint(f"ERROR: dest path exists: {dest}", Color.RED, effect=Color.BOLD)
                    dest_parent = os.path.dirname(dest)
                    if not os.path.exists(dest_parent):
                        print(f"Creating destination parent directory: {dest_parent}")
                        if commit:
                            os.makedirs(dest_parent)
                    if commit:
                        shutil.move(source, dest)
                    Color.print("Moved data:", Color.YELLOW)
                    Color.print(f"  {source} ->", Color.YELLOW)
                    Color.print(f"  {dest}", Color.YELLOW)
                    self._write_entry_to_loc(entry, path=dest_path)
                    changed = True
                    Color.print("Changed table entry:", Color.YELLOW)
                    Color.print(f"  {entry.path} ->", Color.YELLOW)
                    Color.print(f"  {dest_path}", Color.YELLOW)
                    for link_source, link_target in link_map:
                        if commit:
                            os.unlink(link_source)
                            os.symlink(link_source, link_target)
                            assert os.path.exists(link_source)
                        Color.print(f"Remapped symlink: {link_source} -> {link_target}", Color.YELLOW)
                else:
                    self._write_entry_to_loc(entry)
                    Color.print(f"Ok: {entry.path}", Color.GREEN)
            except Exception as exc:
                Color.print(f"ERROR: Encountered an exception while reorganizing data in {self.name} table: {self.loc_file_path}", Color.RED, effect=Color.BOLD)
                Color.print(f"ERROR: Partial loc file rewrite can be found at: {self.new_loc_file_path}", Color.RED, effect=Color.BOLD)
                self.new_loc_file.close()
                raise
            self.new_loc_file.close()
            if changed:
                Color.print("Checking for loc file changes", Color.CYAN)
                subprocess.call(["diff", "-u", self.loc_file_path, self.new_loc_file_path])
                if commit:
                    os.rename(self.new_loc_file_path, self.loc_file_path)
                else:
                    os.unlink(self.new_loc_file_path)
            else:
                Color.print("No changes", Color.CYAN)
                os.unlink(self.new_loc_file_path)

def parse_tdtc(tdtc, tool_data_path):
    tree = ElementTree.parse(tdtc)
    root = tree.getroot()
    assert root.tag == "tables", f"Root telement should be <tables> (was: <{root.tag}>), is this a tool_data_table_conf.xml?: {tdtc}"
    for table in root.findall("table"):
        dt = DataTable.from_elem(table, tool_data_path=tool_data_path)
        if dt.name not in PATH_TEMPLATES:
            Color.print(f"WARNING: no path template for table, skipping: {dt.name}", Color.RED)
            continue
        if dt:
            yield dt


def parse_arguments(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--tool-data-path", required=True, type=pathlib.Path, help="Path to tool data dir")
    parser.add_argument("--commit", default=False, action="store_true", help="Commit changes (otherwise, only print what would be done without making chnages)")
    parser.add_argument("tool_data_table_conf", nargs="+", type=pathlib.Path, help="Path to a tool_data_table_conf.xml")
    return parser.parse_args(argv)


def main(argv=None):
    if not argv:
        argv = sys.argv[1:]
    args = parse_arguments(argv)
    for tdtc in args.tool_data_table_conf:
        Color.print(f"Processing: {tdtc}", Color.BRIGHT_MAGENTA, effect=Color.UNDERLINE)
        for dt in parse_tdtc(tdtc, args.tool_data_path):
            Color.print(f"Data Table: {dt.name}", Color.MAGENTA)
            dt.reorganize(commit=args.commit)


if __name__ == "__main__":
    main()
