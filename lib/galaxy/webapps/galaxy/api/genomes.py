from galaxy.exceptions import (
    ReferenceDataError,
    RequestParameterInvalidException,
)
from galaxy.web import (
    expose_api_anonymous,
    expose_api_raw_anonymous,
)
from galaxy.web.framework.helpers import is_true
from galaxy.webapps.base.controller import BaseAPIController


def get_id(base, format):
    if format:
        return f"{base}.{format}"
    else:
        return base


class GenomesController(BaseAPIController):
    """
    RESTful controller for interactions with genome data.
    """

    @expose_api_anonymous
    def index(self, trans, **kwd):
        """
        GET /api/genomes: returns a list of installed genomes
        """
        return self.app.genomes.get_dbkeys(trans, **kwd)

    @expose_api_anonymous
    def show(self, trans, id, num=None, chrom=None, low=None, high=None, **kwd):
        """
        GET /api/genomes/{id}

        Returns information about build <id>
        """

        # Process kwds.
        id = get_id(id, kwd.get('format', None))
        reference = is_true(kwd.get('reference', False))

        # Return info.
        rval = None
        if reference:
            region = self.app.genomes.reference(trans, dbkey=id, chrom=chrom, low=low, high=high)
            rval = {'dataset_type': 'refseq', 'data': region.sequence}
        else:
            rval = self.app.genomes.chroms(trans, dbkey=id, num=num, chrom=chrom, low=low)
        return rval

    @expose_api_raw_anonymous
    def indexes(self, trans, id, **kwd):
        """
        GET /api/genomes/{id}/indexes?type={table name}

        Returns all available indexes for a genome id for type={table name}
        For instance, /api/genomes/hg19/indexes?type=fasta_indexes
        """
        id = get_id(id, kwd.get('format', None))
        index_type = kwd.get('type', None)
        index_filename = self._get_index_filename(id, index_type)
        try:
            fh = open(index_filename, mode='r')
        except OSError:
            raise ReferenceDataError(f'Failed to load index file for {id}')
        else:
            return fh.read()

    def _get_index_filename(self, id, index_type):
        index_extensions = {'fasta_indexes': '.fai'}
        if index_type not in index_extensions:
            raise RequestParameterInvalidException(f'Invalid index type: {index_type}')

        tbl_entries = self.app.tool_data_tables.data_tables[index_type].data
        try:
            paths = [x[-1] for x in tbl_entries if id in x]
            index_file_name = paths.pop()
        except TypeError:
            raise ReferenceDataError('Data tables not found for {index_type}')
        except IndexError:
            raise ReferenceDataError('Data tables not found for {index_type} for {id}')
        else:
            return index_file_name + index_extensions[index_type]

    @expose_api_raw_anonymous
    def sequences(self, trans, id, num=None, chrom=None, low=None, high=None, **kwd):
        """
        GET /api/genomes/{id}/sequences

        This is a wrapper for accepting sequence requests that
        want a raw return, not json
        """
        id = get_id(id, kwd.get('format', None))
        region = self.app.genomes.reference(trans, dbkey=id, chrom=chrom, low=low, high=high)
        return region.sequence
