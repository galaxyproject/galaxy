#!/usr/bin/env python3
#
# Reorganize tool data to the layout described in https://github.com/galaxyproject/galaxy/discussions/19013
#
import argparse
import os
import pathlib
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
    # path column is path to a symlink to the seq in a directory
    SEQ_LINK = 3
    # path column is path to a file prefix in a directory
    PREFIX = 4


PATH_TEMPLATES = {
    "all_fasta": "{tool_data_path}/genomes/{dbkey}/seq/{value}.fa",
    # __dbkeys__ and twobit only have value, not dbkey, in this case we hope there are no variants
    "twobit": "{tool_data_path}/genomes/{value}/seq/{value}.2bit",
    "__dbkeys__": "{tool_data_path}/genomes/{value}/len/{value}.len",
    "fasta_indexes": "{tool_data_path}/genomes/{dbkey}/sam_fasta_index/v1/{value}/{value}.fa",
    "bowtie_indexes": "{tool_data_path}/genomes/{dbkey}/bowtie_index/v1/{value}/{value}.fa",
    "bowtie2_indexes": "{tool_data_path}/genomes/{dbkey}/bowtie_index/v2/{value}/{value}",
    "tophat2_indexes": "{tool_data_path}/genomes/{dbkey}/bowtie_index/v2/{value}/{value}",
    "bwa_mem_indexes": "{tool_data_path}/genomes/{dbkey}/bwa_mem_index/v1/{value}/{value}.fa",
    "bwa_mem2_indexes": "{tool_data_path}/genomes/{dbkey}/bwa_mem_index/v2/{value}/{value}.fa",
    "hisat2_indexes": "{tool_data_path}/genomes/{dbkey}/hisat_index/v2/{value}/{value}",
    "rnastar_index2x_versioned": "{tool_data_path}/genomes/{dbkey}/rnastar_index/v{version}/{value}",

}

PATH_TYPES = {
    "all_fasta": PathType.FILE,
    "twobit": PathType.FILE,
    "__dbkeys__": PathType.FILE,
    "fasta_indexes": PathType.SEQ_LINK,
    "bowtie_indexes": PathType.SEQ_LINK,
    "bowtie2_indexes": PathType.SEQ_LINK,
    "tophat2_indexes": PathType.SEQ_LINK,
    "bwa_mem_indexes": PathType.SEQ_LINK,
    "bwa_mem2_indexes": PathType.SEQ_LINK,
    "hisat2_indexes": PathType.SEQ_LINK,
    "rnastar_index2x_versioned": PathType.DIRECTORY,
}

LOC_ONLY = {
    "tophat2_indexes",
}

PATH_COLUMNS = {
    "__dbkeys__": "len_path",
}

SEQ_APPEND_EXTENSION = {
    "bowtie2_indexes": ".fa",
    "hisat2_indexes": ".fa",
}


class __dbkeys__(namedtuple("__dbkeys__", ["value", "name", "len_path"])):
    @property
    def path(self):
        return self.len_path


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
    def print(text, color, effect=None, **kwargs):
        print(Color.sprint(text, color, effect=effect), **kwargs)


class LocFile:
    def __init__(self, path, table, comment_char):
        self.file = open(path, "rt")
        self.table = table
        self.comment_char = comment_char

    def __iter__(self):
        for line in self.file:
            line = line.strip()
            if not line.startswith(self.comment_char):
                yield self.table(*line.split("\t"))


class DataTable:
    @classmethod
    def from_elem(cls, elem, tool_data_path=None):
        name = elem.attrib["name"]
        comment_char = elem.attrib.get("comment_char", "#")
        columns = [c.strip() for c in elem.find("columns").text.split(",")]
        loc_file_path = elem.find("file").attrib["path"].strip()
        if name not in PATH_TEMPLATES:
            Color.print(f"WARNING: no path template for table: {name}", Color.RED)
            return None
        if not os.path.exists(loc_file_path):
            Color.print(f"WARNING: loc file for table {name} does not exist: {loc_file_path}", Color.RED)
            return None
        return cls(name, columns, loc_file_path, comment_char, tool_data_path=tool_data_path)

    def __init__(self, name, columns, loc_file_path, comment_char, tool_data_path=None):
        self.name = name
        self.columns = columns
        self.loc_file_path = loc_file_path
        self.comment_char = comment_char
        if name == "__dbkeys__":
            self.table = __dbkeys__
        else:
            self.table = namedtuple(name, columns)
        self._tool_data_path = tool_data_path
        self.loc_file = LocFile(loc_file_path, self.table, comment_char)
        self._initialize_new_loc_file()

    def _initialize_new_loc_file(self):
        fd, self.new_loc_file_path = tempfile.mkstemp(
            suffix=".reorganize_tool_data.loc",
            prefix=f"{self.name}.",
            #dir=os.path.dirname(self.loc_file_path),
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

    @property
    def symlink_seq(self):
        return self.path_type == PathType.SEQ_LINK

    @property
    def move_data(self):
        return self.name not in LOC_ONLY

    @property
    def path_column(self):
        return PATH_COLUMNS.get(self.name, "path")

    def _table_path(self, entry, table=None):
        table = table or self.name
        template_dict = {"tool_data_path": self.tool_data_path}
        template_dict.update(entry._asdict())
        return PATH_TEMPLATES[table].format(**template_dict)

    def _source_path(self, entry):
        if self.path_type in (PathType.FILE, PathType.DIRECTORY):
            return entry.path
        elif self.path_type in (PathType.SEQ_LINK, PathType.PREFIX):
            return os.path.dirname(entry.path)
        else:
            raise NotImplementedError(self.path_type)

    def _dest_path(self, entry):
        if self.path_type in (PathType.FILE, PathType.DIRECTORY):
            return self._table_path(entry)
        elif self.path_type in (PathType.SEQ_LINK, PathType.PREFIX):
            return os.path.dirname(self._table_path(entry))
        else:
            raise NotImplementedError(self.path_type)

    def _symlink_seq(self, entry, commit=False):
        if self.symlink_seq:
            append = SEQ_APPEND_EXTENSION.get(self.name, "")
            table_path = self._table_path(entry) + append
            if commit:
                path = table_path
            else:
                path = entry.path + append
            if os.path.exists(path) and not os.path.islink(path):
                Color.print(f"WARNING: Expected sequence link exists but is not a link: {path}", Color.RED)
                return
            assert os.path.islink(path), Color.sprint(f"Expected sequence link is not a link (or does not exist): {path}", Color.RED, effect=Color.BOLD)
            seq_path = self._table_path(entry, table="all_fasta")
            link_target = os.path.relpath(seq_path, start=os.path.dirname(table_path))
            if commit:
                os.unlink(table_path)
                os.symlink(table_path, link_target)
            Color.print(f"Remapped seq symlink: {table_path} -> {link_target}", Color.YELLOW)

    def _write_entry_to_loc(self, entry, path=None):
        if path:
            new_entry_dict = entry._asdict()
            new_entry_dict.update({self.path_column: path})
            new_entry = self.table(**new_entry_dict)
        else:
            new_entry = entry
        new_entry_str = "\t".join(new_entry)
        self.new_loc_file.write(f"{new_entry_str}\n")

    def _move_entry(self, entry, dest_path, commit=False):
        source = self._source_path(entry)
        dest = self._dest_path(entry)
        assert os.path.lexists(source) and os.path.exists(source), Color.sprint(
                f"ERROR: source path does not exist: {source}", Color.RED, effect=Color.BOLD)
        assert not os.path.exists(dest), Color.sprint(
                f"ERROR: dest path exists: {dest}", Color.RED, effect=Color.BOLD)
        if self.move_data:
            dest_parent = os.path.dirname(dest)
            if not os.path.exists(dest_parent):
                print(f"Creating destination parent directory: {dest_parent}")
                if commit:
                    os.makedirs(dest_parent)
            Color.print("Moving data:", Color.YELLOW)
            Color.print(f"  {source} ->", Color.YELLOW)
            Color.print(f"  {dest}", Color.YELLOW)
            if commit:
                shutil.move(source, dest)
            self._symlink_seq(entry, commit=commit)
        self._write_entry_to_loc(entry, path=dest_path)
        Color.print("Changed table entry:", Color.YELLOW)
        Color.print(f"  {entry.path} ->", Color.YELLOW)
        Color.print(f"  {dest_path}", Color.YELLOW)

    def reorganize(self, commit=False):
        changed = False
        try:
            for entry in self.loc_file:
                dest_path = self._table_path(entry)
                if dest_path != entry.path:
                    self._move_entry(entry, dest_path, commit=commit)
                    changed = True
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
            Color.print("Changes to .loc file:", Color.CYAN, flush=True)
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
