import ast
import html
import io
import uuid as _uuid
import zipfile
from typing import (
    Dict,
    List,
    Optional,
)

import yaml

from galaxy.datatypes.binary import CompressedZipArchive
from galaxy.datatypes.metadata import MetadataElement
from galaxy.datatypes.protocols import (
    DatasetProtocol,
    HasMetadata,
)
from galaxy.datatypes.sniff import (
    build_sniff_from_prefix,
    FilePrefix,
)
from galaxy.datatypes.tabular import Tabular


class _QIIME2ResultBase(CompressedZipArchive):
    """Base class for QIIME2Artifact and QIIME2Visualization"""

    MetadataElement(name="semantic_type", readonly=True)
    MetadataElement(name="semantic_type_simple", readonly=True, visible=False)
    MetadataElement(name="uuid", readonly=True)
    MetadataElement(name="format", optional=True, no_value="", readonly=True)
    MetadataElement(name="version", readonly=True)

    def set_meta(self, dataset: DatasetProtocol, overwrite: bool = True, **kwd) -> None:
        metadata = _get_metadata_from_archive(dataset.file_name)
        for key, value in metadata.items():
            if value:
                setattr(dataset.metadata, key, value)

        dataset.metadata.semantic_type_simple = _strip_properties(dataset.metadata.semantic_type)

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        if dataset.metadata.semantic_type == "Visualization":
            dataset.blurb = "QIIME 2 Visualization"
        else:
            dataset.blurb = "QIIME 2 Artifact"

        dataset.peek = "\n".join(map(": ".join, self._peek(dataset)))

    def display_peek(self, dataset: DatasetProtocol) -> str:
        def make_row(item):
            return "<tr><th>%s</th><td>%s</td></td>" % tuple(html.escape(x) for x in item)

        table = ['<table cellspacing="0" cellpadding="2">']
        table += list(map(make_row, self._peek(dataset, simple=True)))
        table += ["</table>"]

        return "".join(table)

    def _peek(self, dataset: HasMetadata, simple: bool = False) -> List:
        peek = [("Type", dataset.metadata.semantic_type), ("UUID", dataset.metadata.uuid)]
        if not simple:
            if dataset.metadata.semantic_type != "Visualization":
                peek.append(("Format", dataset.metadata.format))
            peek.append(("Version", dataset.metadata.version))
        return peek

    def _sniff(self, filename: str) -> Optional[Dict]:
        """Helper method for use in inherited datatypes"""
        try:
            if not zipfile.is_zipfile(filename):
                raise Exception()
            return _get_metadata_from_archive(filename)
        except Exception:
            return None


class QIIME2Artifact(_QIIME2ResultBase):
    file_ext = "qza"

    def sniff(self, filename: str) -> bool:
        metadata = self._sniff(filename)
        return bool(metadata) and metadata["semantic_type"] != "Visualization"  # type: ignore[index]


class QIIME2Visualization(_QIIME2ResultBase):
    file_ext = "qzv"

    def sniff(self, filename: str) -> bool:
        metadata = self._sniff(filename)
        return bool(metadata) and metadata["semantic_type"] == "Visualization"  # type: ignore[index]


@build_sniff_from_prefix
class QIIME2Metadata(Tabular):
    """
    QIIME 2 supports overriding the type of a column to Categorical when
    a specific directive `#q2:types` is present under the ID row.

    Galaxy already understands column types quite well, however we sometimes
    want to override its inferred type.

    For Galaxy, we are going to require that if a directive occurs, it happens
    on the second line (after the header). This is the most typical location
    and interacts best with the current implementation of Tabular.
    """

    file_ext = "qiime2.tabular"

    _TYPES_DIRECTIVE = "#q2:types"
    _search_lines = 2

    def get_column_names(self, first_line: str) -> Optional[List[str]]:
        return first_line.strip().split("\t")

    def set_meta(self, dataset: DatasetProtocol, overwrite: bool = True, **kwd) -> None:
        """
        Let Galaxy's Tabular format handle most of this. We will just jump
        in at the last minute to (potentially) override some column types.
        """
        super().set_meta(dataset, overwrite=overwrite, **kwd)

        if dataset.has_data():
            with open(dataset.file_name) as dataset_fh:
                line = None
                for line, _ in zip(dataset_fh, range(self._search_lines)):
                    if line.startswith(self._TYPES_DIRECTIVE):
                        break
                if line is None:
                    return

            q2_types = line.strip().split("\t")
            # The first column (q2:types) is always the IDs
            q2_types[0] = "index"

            if len(q2_types) < dataset.metadata.columns:
                # this is probably malformed, but easy to fix
                q2_types.extend([""] * (dataset.metadata.columns - len(q2_types)))

            for idx, (q2_type, col_type) in enumerate(zip(q2_types, dataset.metadata.column_types)):
                if q2_type == "":
                    if col_type in ("float", "int"):
                        q2_types[idx] = "numeric"
                    else:
                        q2_types[idx] = "categorical"
                else:
                    if q2_type == "categorical" and col_type in ("float", "int", "list"):
                        dataset.metadata.column_types[idx] = "str"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        for _, line in zip(range(self._search_lines), file_prefix.line_iterator()):
            if line.startswith(self._TYPES_DIRECTIVE):
                return True

        return False


##############################################################################
# Helpers
##############################################################################


def _strip_properties(expression):
    # This is necessary because QIIME 2's semantic types include a limited
    # form of intersection type, which means that `A & B` is a subtype of `A`
    # as well as a subtype of `B`. This means it is not generally speaking
    # possible or practical to enumerate all valid subtypes and then do an
    # exact match using <options options_filter_attribute="Some[Type]">
    # So instead filter out 90% of the invalid inputs and let QIIME 2 raise an
    # error on the finer details such as these "properties".
    try:
        expression_tree = ast.parse(expression)
        reconstructer = _PredicateRemover()
        reconstructer.visit(expression_tree)
        return reconstructer.expression
    # If we have any problems stripping properties just use the full expression
    # this punts the error off to q2galaxy so if we error we do so there and
    # not here
    except Exception:
        return expression


# Python 3.9 has a built in unparse. We can probably use this in the future
# when we are using 3.9
# https://docs.python.org/3.9/library/ast.html#ast.unparse
class _PredicateRemover(ast.NodeVisitor):
    binops = {
        ast.Add: " + ",
        ast.Sub: " - ",
        ast.Mult: " * ",
        ast.Div: " / ",
        ast.FloorDiv: " // ",
        ast.Pow: " ** ",
        ast.LShift: " << ",
        ast.RShift: " >> ",
        ast.BitOr: " | ",
        ast.BitXor: " ^ ",
        ast.BitAnd: " & ",
        ast.MatMult: " @ ",
    }

    def __init__(self):
        self.expression = ""

    def visit_Name(self, node):
        self.expression += node.id

    def visit_Subscript(self, node):
        self.visit(node.value)
        self.expression += "["
        self.visit(node.slice)
        self.expression += "]"

    def visit_Tuple(self, node):
        trailing_comma = ""
        for n in node.elts:
            self.expression += trailing_comma
            self.visit(n)
            trailing_comma = ", "

    def visit_BinOp(self, node):
        self.visit(node.left)
        if not isinstance(node.op, ast.Mod):
            self.expression += self.binops[node.op.__class__]
            self.visit(node.right)


def _get_metadata_from_archive(archive):
    uuid = _get_uuid(archive)
    archive_version, framework_version = _get_versions(archive, uuid)
    metadata_contents = _get_metadata_contents(archive, uuid)

    return {
        "uuid": uuid,
        "version": framework_version,
        "semantic_type": metadata_contents["type"],
        "format": metadata_contents["format"] or "",
    }


def _get_metadata_contents(path, uuid):
    with _open_file_in_archive(path, "metadata.yaml", uuid) as fh:
        return yaml.safe_load(fh.read())


def _get_uuid(path):
    roots = set()
    for relpath in _iter_zip_root(path):
        if not relpath.startswith("."):
            roots.add(relpath)

    if len(roots) == 0:
        raise ValueError("Archive does not have a visible root directory.")
    if len(roots) > 1:
        raise ValueError("Archive has multiple root directories: %r" % roots)
    uuid = roots.pop()
    if not _is_uuid4(uuid):
        raise ValueError("Archive root directory name %r is not a valid version 4 " "UUID." % uuid)
    return uuid


def _get_versions(path, uuid):
    try:
        with _open_file_in_archive(path, "VERSION", uuid) as fh:
            header, version_line, framework_version_line, eof = fh.read().split("\n")
        if header.strip() != "QIIME 2":
            raise Exception()  # GOTO except Exception
        version = version_line.split(":")[1].strip()
        framework_version = framework_version_line.split(":")[1].strip()
        return version, framework_version
    except Exception:
        raise ValueError("Archive does not contain a correctly formatted" " VERSION file.")


def _open_file_in_archive(zip_path, path, uuid):
    relpath = "/".join([uuid, path])
    with zipfile.ZipFile(zip_path, mode="r") as zf:
        return io.TextIOWrapper(zf.open(relpath))


def _iter_zip_root(path):
    seen = set()
    with zipfile.ZipFile(path, mode="r") as zf:
        for name in zf.namelist():
            parts = name.split("/")  # zip is always / for seperators
            if len(parts) > 0:
                result = parts[0]
                if result not in seen:
                    seen.add(result)
                    yield result


def _is_uuid4(uuid_str):
    # Adapted from https://gist.github.com/ShawnMilo/7777304
    try:
        uuid = _uuid.UUID(hex=uuid_str, version=4)
    except ValueError:
        # The string is not a valid hex code for a UUID.
        return False

    # If uuid_str is a valid hex code, but an invalid uuid4, UUID.__init__
    # will convert it to a valid uuid4.
    return str(uuid) == uuid_str
