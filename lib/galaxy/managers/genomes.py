from typing import (
    Any,
    Optional,
    TYPE_CHECKING,
)

from sqlalchemy import (
    func,
    text,
)

from galaxy.exceptions import ReferenceDataError
from galaxy.managers.context import ProvidesUserContext
from galaxy.model import User
from galaxy.model.database_utils import is_postgres
from galaxy.structured_app import (
    MinimalManagerApp,
    StructuredApp,
)
from .base import raise_filter_err

if TYPE_CHECKING:
    from galaxy.managers.base import OrmFilterParsersType


class GenomesManager:
    def __init__(self, app: StructuredApp):
        self._app = app
        self.genomes = app.genomes

    def get_dbkeys(self, user: Optional[User], chrom_info: bool) -> list[list[str]]:
        return self.genomes.get_dbkeys(user, chrom_info)

    def get_dbkeys_indexes(self) -> list[list[str]]:
        tbl_entries = self._get_tbl_entries()
        # return display_name and unique_build_id
        return [[x[2], x[0]] for x in tbl_entries]

    def is_registered_dbkey(self, dbkey: str, user: Optional[User]) -> bool:
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

    def get_indexes(self, id: str) -> str:
        index_filename = self.get_indexes_filename(id)
        try:
            with open(f"{index_filename}.fai") as f:
                return f.read()
        except OSError:
            raise ReferenceDataError(f"Failed to load index file for {id}")

    def get_indexes_filename(self, id: str) -> str:
        tbl_entries = self._get_tbl_entries()
        paths = [x[-1] for x in tbl_entries if id in x]
        if not paths:
            raise ReferenceDataError(f"Data tables not found for fasta_indexes for {id}")
        return paths.pop()

    def _get_tbl_entries(self):
        try:
            return self._app.tool_data_tables.data_tables["fasta_indexes"].data
        except TypeError:
            raise ReferenceDataError("Data table not found for fasta_indexes")


class GenomeFilterMixin:
    app: MinimalManagerApp
    orm_filter_parsers: "OrmFilterParsersType"
    valid_ops = ("eq", "contains", "has")

    def create_genome_filter(self, attr, op, val):
        def _create_genome_filter(model_class=None):
            if op not in GenomeFilterMixin.valid_ops:
                raise_filter_err(attr, op, val, "bad op in filter")
            if model_class is None:
                return True
            # Doesn't filter genome_build for collections
            if model_class.__name__ == "HistoryDatasetCollectionAssociation":
                return False
            if is_postgres(self.app.config.database_connection):
                column = text("convert_from(metadata, 'UTF8')::json ->> 'dbkey'")
            else:
                column = func.json_extract(model_class.table.c._metadata, "$.dbkey")  # type:ignore[assignment]
            lower_val = val.lower()  # Ignore case
            # dbkey can either be "hg38" or '["hg38"]', so we need to check both
            if op == "eq":
                cond = func.lower(column) == lower_val or func.lower(column) == f'["{lower_val}"]'
            else:
                cond = func.lower(column).contains(lower_val, autoescape=True)
            return cond

        return _create_genome_filter

    def _add_parsers(self):
        self.orm_filter_parsers.update({"genome_build": self.create_genome_filter})
