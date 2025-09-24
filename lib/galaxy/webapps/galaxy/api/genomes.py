from typing import (
    Any,
)

from fastapi import (
    Path,
    Query,
)
from fastapi.responses import Response

from galaxy.managers.context import ProvidesUserContext
from galaxy.managers.genomes import GenomesManager
from galaxy.webapps.base.api import GalaxyFileResponse
from . import (
    depends,
    DependsOnTrans,
    Router,
)

router = Router(tags=["genomes"])

IdPathParam: str = Path(..., title="Genome ID", description="Genome ID")

IndexesQueryParam: bool = Query(False, title="Indexes", description="If true, return genome ids of available indexes")

ChromInfoQueryParam: bool = Query(
    None, title="ChromInfo", description="If true, return genome keys with chromosome lengths"
)

NumQueryParam: int = Query(
    None,
    title="Number",
    description="Limits size of returned data",
)

ChromQueryParam: Any = Query(
    None,
    title="Chrom",
    description="Limits size of returned data",
)

LowQueryParam: int = Query(
    None,
    title="Low",
    description="Limits size of returned data",
)

HighQueryParam: int = Query(
    None,
    title="High",
    description="Limits size of returned data",
)

FormatQueryParam: str = Query(None, title="Format", description="Format")

ReferenceQueryParam: bool = Query(None, title="Reference", description="If true, return reference data")

IndexTypeQueryParam: str = Query(
    "fasta_indexes", title="Index type", description="Index type"  # currently this is the only supported index type
)


def get_id(base, format):
    if format:
        return f"{base}.{format}"
    return base


@router.cbv
class FastAPIGenomes:
    manager: GenomesManager = depends(GenomesManager)

    @router.get("/api/genomes", summary="Return a list of installed genomes", response_description="Installed genomes")
    def index(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        chrom_info: bool = ChromInfoQueryParam,
        indexes: bool = IndexesQueryParam,
    ) -> list[list[str]]:
        if indexes:
            return self.manager.get_dbkeys_indexes()
        return self.manager.get_dbkeys(trans.user, chrom_info)

    @router.get(
        "/api/genomes/{id}",
        summary="Return information about build <id>",
        response_description="Information about genome build <id>",
    )
    def show(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        id: str = IdPathParam,
        reference: bool = ReferenceQueryParam,
        num: int = NumQueryParam,
        chrom: str = ChromQueryParam,
        low: int = LowQueryParam,
        high: int = HighQueryParam,
        format: str = FormatQueryParam,
    ) -> Any:
        id = get_id(id, format)
        return self.manager.get_genome(trans, id, num, chrom, low, high, reference)

    @router.get(
        "/api/genomes/{id}/indexes",
        summary="Return all available indexes for a genome id",
        response_description="Indexes for a genome id",
    )
    def indexes(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        id: str = IdPathParam,
        type: str = IndexTypeQueryParam,
        format: str = FormatQueryParam,
    ) -> Response:
        id = get_id(id, format)
        rval = self.manager.get_indexes(id)
        return Response(rval)

    @router.get(
        "/api/genomes/{id}/sequences", summary="Return raw sequence data", response_description="Raw sequence data"
    )
    def sequences(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        id: str = IdPathParam,
        chrom: str = ChromQueryParam,
        low: int = LowQueryParam,
        high: int = HighQueryParam,
        format: str = FormatQueryParam,
    ) -> Response:
        id = get_id(id, format)
        rval = self.manager.get_sequence(trans, id, chrom, low, high)
        return Response(rval)

    @router.get(
        "/api/genomes/{id}/download",
        summary="Return sequence data for download",
        response_description="Sequence data file",
        response_class=GalaxyFileResponse,
    )
    def download(self, trans: ProvidesUserContext = DependsOnTrans, id: str = IdPathParam) -> GalaxyFileResponse:
        filename = self.manager.get_indexes_filename(id)
        return GalaxyFileResponse(filename)
