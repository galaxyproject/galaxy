from typing import (
    Any,
    List,
)

from fastapi import (
    Path,
    Query,
)
from fastapi.responses import Response

from galaxy.managers.context import ProvidesUserContext
from galaxy.managers.genomes import GenomesManager
from galaxy.web import (
    expose_api_anonymous_and_sessionless,
    expose_api_raw_anonymous_and_sessionless,
)
from galaxy.web.framework.helpers import is_true
from . import (
    BaseGalaxyAPIController,
    depends,
    DependsOnTrans,
    Router,
)

router = Router(tags=["genomes"])

IdPathParam: str = Path(..., title="Genome ID", description="Genome ID")

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
        self, trans: ProvidesUserContext = DependsOnTrans, chrom_info: bool = ChromInfoQueryParam
    ) -> List[List[str]]:
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
        summary="Return all available indexes for a genome id for provided type",
        response_description="Indexes for a genome id for provided type",
    )
    def indexes(
        self,
        id: str = IdPathParam,
        type: str = IndexTypeQueryParam,
        format: str = FormatQueryParam,
    ) -> Any:
        id = get_id(id, format)
        rval = self.manager.get_indexes(id, type)
        return Response(rval)

    @router.get(
        "/api/genomes/{id}/sequences", summary="Return raw sequence data", response_description="Raw sequence data"
    )
    def sequences(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        id: str = IdPathParam,
        reference: bool = ReferenceQueryParam,
        chrom: str = ChromQueryParam,
        low: int = LowQueryParam,
        high: int = HighQueryParam,
        format: str = FormatQueryParam,
    ) -> Any:
        id = get_id(id, format)
        rval = self.manager.get_sequence(trans, id, chrom, low, high)
        return Response(rval)


class GenomesController(BaseGalaxyAPIController):
    """
    RESTful controller for interactions with genome data.
    """

    manager: GenomesManager = depends(GenomesManager)

    @expose_api_anonymous_and_sessionless
    def index(self, trans, **kwd):
        """
        GET /api/genomes: returns a list of installed genomes
        ---
        get:
            description: returns a list of installed genomes
            responses:
                200:
                    content:
                        application/json:
                            schema:
                                type: array
                                items:
                                    type: string
        """
        chrom_info = kwd.get("chrom_info")
        return self.manager.get_dbkeys(trans.user, chrom_info)

    @expose_api_anonymous_and_sessionless
    def show(self, trans, id, num=None, chrom=None, low=None, high=None, **kwd):
        """
        GET /api/genomes/{id}

        Returns information about build <id>
        """
        id = get_id(id, kwd.get("format"))
        reference = is_true(kwd.get("reference", False))
        return self.manager.get_genome(trans, id, num, chrom, low, high, reference)

    @expose_api_raw_anonymous_and_sessionless
    def indexes(self, trans, id, **kwd):
        """
        GET /api/genomes/{id}/indexes?type={table name}

        Returns all available indexes for a genome id for type={table name}
        For instance, /api/genomes/hg19/indexes?type=fasta_indexes
        """
        id = get_id(id, kwd.get("format"))
        index_type = kwd.get("type")
        return self.manager.get_indexes(id, index_type)

    @expose_api_raw_anonymous_and_sessionless
    def sequences(self, trans, id, chrom=None, low=None, high=None, **kwd):
        """
        GET /api/genomes/{id}/sequences

        This is a wrapper for accepting sequence requests that
        want a raw return, not json
        """
        id = get_id(id, kwd.get("format"))
        return self.manager.get_sequence(trans, id, chrom, low, high)
