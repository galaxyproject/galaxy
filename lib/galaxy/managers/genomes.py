from typing import (
    Any,
    List,
)

from galaxy import model as m
from galaxy.exceptions import (
    ReferenceDataError,
    RequestParameterInvalidException,
)
from galaxy.managers.context import ProvidesUserContext
from galaxy.structured_app import StructuredApp


class GenomesManager:
    def __init__(self, app: StructuredApp):
        self._app = app
        self.genomes = app.genomes

    def get_dbkeys(self, user: m.User, chrom_info: bool) -> List[List[str]]:
        return self.genomes.get_dbkeys(user, chrom_info)

    def is_registered_dbkey(self, dbkey: str, user: m.User) -> bool:
        dbkeys = self.get_dbkeys(user, chrom_info=False)
        for _, key in dbkeys:
            if dbkey == key:
                return True
        return False

    def get_genome(
        self, trans: ProvidesUserContext, id: str, num: int, chrom: str, low: int, high: int, reference: bool
    ) -> Any:
        if reference:
            region = self.genomes.reference(trans, dbkey=id, chrom=chrom, low=low, high=high)
            return {"dataset_type": "refseq", "data": region.sequence}
        else:
            return self.genomes.chroms(trans, dbkey=id, num=num, chrom=chrom, low=low)

    def get_sequence(self, trans: ProvidesUserContext, id: str, chrom: str, low: int, high: int) -> Any:
        region = self.genomes.reference(trans, dbkey=id, chrom=chrom, low=low, high=high)
        return region.sequence

    def get_indexes(self, id: str, index_type: str) -> Any:
        index_extensions = {"fasta_indexes": ".fai"}
        if index_type not in index_extensions:
            raise RequestParameterInvalidException(f"Invalid index type: {index_type}")

        tbl_entries = self._app.tool_data_tables.data_tables[index_type].data
        ext = index_extensions[index_type]
        index_filename = self._get_index_filename(id, tbl_entries, ext, index_type)
        try:
            with open(index_filename) as f:
                return f.read()
        except OSError:
            raise ReferenceDataError(f"Failed to load index file for {id}")

    def _get_index_filename(self, id, tbl_entries, ext, index_type):
        try:
            paths = [x[-1] for x in tbl_entries if id in x]
            file_name = paths.pop()
        except TypeError:
            raise ReferenceDataError(f"Data tables not found for {index_type}")
        except IndexError:
            raise ReferenceDataError(f"Data tables not found for {index_type} for {id}")
        else:
            return f"{file_name}{ext}"
