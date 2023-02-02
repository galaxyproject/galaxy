"""
spaln Composite Dataset
"""

import logging
import os.path
from typing import (
    Callable,
    Dict,
    List,
    Optional,
)

from galaxy.datatypes.data import Data
from galaxy.datatypes.metadata import MetadataElement
from galaxy.datatypes.protocols import (
    DatasetHasHidProtocol,
    DatasetProtocol,
    HasExtraFilesAndMetadata,
)
from galaxy.util import smart_str

log = logging.getLogger(__name__)
verbose = True


class _SpalnDb(Data):
    composite_type = "auto_primary_file"

    MetadataElement(
        name="spalndb_name",
        default="spalndb",
        desc="DB name",
        readonly=True,
        visible=True,
        set_in_upload=True,
    )

    def __init__(self, **kwd):
        super().__init__(**kwd)
        self.add_composite_file(
            "%s.ent",
            is_binary=True,
            description="spalndb.ent",
            substitute_name_with_metadata="spalndb_name",
        )
        self.add_composite_file(
            "%s.grp",
            is_binary=True,
            description="spalndb.grp",
            substitute_name_with_metadata="spalndb_name",
        )
        self.add_composite_file(
            "%s.idx",
            is_binary=True,
            description="spalndb.idx",
            substitute_name_with_metadata="spalndb_name",
        )
        self.add_composite_file(
            "%s.seq",
            is_binary=True,
            description="spalndb.seq",
            substitute_name_with_metadata="spalndb_name",
        )

    def generate_primary_file(self, dataset: HasExtraFilesAndMetadata) -> str:
        rval = ["<html><head><title>Spaln Database</title></head><p/>"]
        rval.append("<div>This composite dataset is composed of the following files:<p/><ul>")
        for composite_name, composite_file in self.get_composite_files(dataset=dataset).items():
            fn = composite_name
            opt_text = ""
            if composite_file.get("description"):
                rval.append(
                    '<li><a href="%s" type="application/binary">%s (%s)</a>%s</li>'
                    % (fn, fn, composite_file.get("description"), opt_text)
                )
            else:
                rval.append(f'<li><a href="{fn}" type="application/binary">{fn}</a>{opt_text}</li>')
        rval.append("</ul></div></html>")
        return "\n".join(rval)

    def regenerate_primary_file(self, dataset: DatasetProtocol) -> None:
        """
        cannot do this until we are setting metadata
        """
        efp = dataset.extra_files_path
        flist = os.listdir(efp)
        rval = [
            "<html><head><title>Files for Composite Dataset %s</title></head><body><p/>Composite %s contains:<p/><ul>"
            % (dataset.name, dataset.name)
        ]
        for fname in flist:
            sfname = os.path.split(fname)[-1]
            f, e = os.path.splitext(fname)
            rval.append(f'<li><a href="{sfname}">{sfname}</a></li>')
        rval.append("</ul></body></html>")
        with open(dataset.file_name, "w") as f:
            f.write("\n".join(rval))
            f.write("\n")

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        """Set the peek and blurb text."""
        if not dataset.dataset.purged:
            dataset.peek = "spaln database (multiple files)"
            dataset.blurb = "spaln database (multiple files)"
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def display_peek(self, dataset: DatasetProtocol) -> str:
        """Create HTML content, used for displaying peek."""
        try:
            return dataset.peek
        except Exception:
            return "spaln database (multiple files)"

    def display_data(
        self,
        trans,
        dataset: DatasetHasHidProtocol,
        preview: bool = False,
        filename: Optional[str] = None,
        to_ext: Optional[str] = None,
        offset: Optional[int] = None,
        ck_size: Optional[int] = None,
        **kwd,
    ):
        """
        If preview is `True` allows us to format the data shown in the central pane via the "eye" icon.
        If preview is `False` triggers download.
        """
        headers = kwd.get("headers", {})
        if not preview:
            return super().display_data(
                trans,
                dataset=dataset,
                preview=preview,
                filename=filename,
                to_ext=to_ext,
                offset=offset,
                ck_size=ck_size,
                headers=headers,
                **kwd,
            )
        if self.file_ext == "spalndbn":
            title = "This is a nucleotide-query spaln database"
        elif self.file_ext == "spalndbp":
            title = "This is a protein-query spaln database"
        elif self.file_ext == "spalndba":
            title = "This is a protein spaln database"
        else:
            # Error?
            title = "This is a spaln database (unknown format)."
        msg = ""
        try:
            # Try to use any text recorded in the dummy index file:
            with open(dataset.file_name, encoding="utf-8") as handle:
                msg = handle.read().strip()
        except Exception:
            pass
        if not msg:
            msg = title
        # Galaxy assumes HTML for the display of composite datatypes,
        return (
            smart_str(f"<html><head><title>{title}</title></head><body><pre>{msg}</pre></body></html>"),
            headers,
        )

    @staticmethod
    def merge(split_files: List[str], output_file: str) -> None:
        """Merge spaln databases (not implemented)."""
        raise NotImplementedError("Merging spaln databases is not possible")

    @classmethod
    def split(cls, input_datasets: List, subdir_generator_function: Callable, split_params: Dict) -> None:
        """Split a spaln database (not implemented)."""
        if split_params is None:
            return None
        raise NotImplementedError("Can't split spaln database")

    def set_meta(self, dataset: DatasetProtocol, overwrite: bool = True, **kwd) -> None:
        super().set_meta(dataset, overwrite=overwrite, **kwd)
        efp = dataset.extra_files_path
        for filename in os.listdir(efp):
            if filename.endswith(".ent"):
                dataset.metadata.spalndb_name = os.path.splitext(filename)[0]
        self.regenerate_primary_file(dataset)


class SpalnNuclDb(_SpalnDb):
    file_ext = "spalndbnp"

    def __init__(self, **kwd):
        super().__init__(**kwd)
        self.add_composite_file(
            "%s.bkn",
            is_binary=True,
            description="spalndb.bkn",
            substitute_name_with_metadata="spalndb_name",
        )
        self.add_composite_file(
            "%s.bkp",
            is_binary=True,
            description="spalndb.bkp",
            substitute_name_with_metadata="spalndb_name",
        )


class SpalnProtDb(_SpalnDb):
    file_ext = "spalndba"

    def __init__(self, **kwd):
        super().__init__(**kwd)
        self.add_composite_file(
            "%s.bka",
            is_binary=True,
            description="spalndb.bka",
            substitute_name_with_metadata="spalndb_name",
        )
