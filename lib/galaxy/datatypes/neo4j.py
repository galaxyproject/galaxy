"""
Neo4j Composite Dataset
"""
import logging
import sys

from galaxy.datatypes.data import Data
from galaxy.datatypes.images import Html
from galaxy.datatypes.metadata import MetadataElement

gal_Log = logging.getLogger(__name__)
verbose = True


class Neo4j(Html):
    """
    base class to use for neostore datatypes
    derived from html - composite datatype elements
    stored in extra files path
    """

    def generate_primary_file(self, dataset=None):
        """
        This is called only at upload to write the html file
        cannot rename the datasets here - they come with the default unfortunately
        """
        # self.regenerate_primary_file(dataset)
        rval = [
            '<html><head><title>Files for Composite Dataset (%s)</title></head><p/>\
            This composite dataset is composed of the following files:<p/><ul>' % (
                self.file_ext)]
        for composite_name, composite_file in self.get_composite_files(dataset=dataset).items():
            opt_text = ''
            if composite_file.optional:
                opt_text = ' (optional)'
            rval.append('<li><a href="%s">%s</a>%s' %
                        (composite_name, composite_name, opt_text))
        rval.append('</ul></html>')
        return "\n".join(rval)

    def get_mime(self):
        """Returns the mime type of the datatype"""
        return 'text/html'

    def set_peek(self, dataset, is_multi_byte=False):
        """Set the peek and blurb text"""
        if not dataset.dataset.purged:
            dataset.peek = 'Neo4j database (multiple files)'
            dataset.blurb = 'Neo4j database (multiple files)'
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def display_peek(self, dataset):
        """Create HTML content, used for displaying peek."""
        try:
            return dataset.peek
        except Exception:
            return "NEO4J database (multiple files)"


class Neo4jDB(Neo4j, Data):
    """Class for neo4jDB database files."""
    file_ext = 'neostore'
    composite_type = 'auto_primary_file'
    allow_datatype_change = False

    def __init__(self, **kwd):
        Data.__init__(self, **kwd)
        self.add_composite_file('neostore', is_binary=True)
        self.add_composite_file('neostore.id', is_binary=True)
        self.add_composite_file('neostore.counts.db.a', optional=True, is_binary=True)
        self.add_composite_file('neostore.counts.db.b', optional=True, is_binary=True)
        self.add_composite_file('neostore.labeltokenstore.db', is_binary=True)
        self.add_composite_file(
            'neostore.labeltokenstore.db.id', is_binary=True)
        self.add_composite_file(
            'neostore.labeltokenstore.db.names', is_binary=True)
        self.add_composite_file(
            'neostore.labeltokenstore.db.names.id', is_binary=True)
        self.add_composite_file('neostore.nodestore.db', is_binary=True)
        self.add_composite_file('neostore.nodestore.db.id', is_binary=True)
        self.add_composite_file('neostore.nodestore.db.labels', is_binary=True)
        self.add_composite_file(
            'neostore.nodestore.db.labels.id', is_binary=True)

        self.add_composite_file('neostore.propertystore.db', is_binary=True)
        self.add_composite_file('neostore.propertystore.db.id', is_binary=True)
        self.add_composite_file(
            'neostore.propertystore.db.arrays', is_binary=True)
        self.add_composite_file(
            'neostore.propertystore.db.arrays.id', is_binary=True)
        self.add_composite_file(
            'neostore.propertystore.db.index', is_binary=True)
        self.add_composite_file(
            'neostore.propertystore.db.index.id', is_binary=True)
        self.add_composite_file(
            'neostore.propertystore.db.index.keys', is_binary=True)
        self.add_composite_file(
            'neostore.propertystore.db.index.keys.id', is_binary=True)
        self.add_composite_file(
            'neostore.propertystore.db.strings', is_binary=True)
        self.add_composite_file(
            'neostore.propertystore.db.strings.id', is_binary=True)

        self.add_composite_file(
            'neostore.relationshipgroupstore.db', is_binary=True)
        self.add_composite_file(
            'neostore.relationshipgroupstore.db.id', is_binary=True)
        self.add_composite_file(
            'neostore.relationshipstore.db', is_binary=True)
        self.add_composite_file(
            'neostore.relationshipstore.db.id', is_binary=True)
        self.add_composite_file(
            'neostore.relationshiptypestore.db.names', is_binary=True)
        self.add_composite_file(
            'neostore.relationshiptypestore.db.names.id', is_binary=True)
        self.add_composite_file('neostore.schemastore.db', is_binary=True)
        self.add_composite_file('neostore.schemastore.db.id', is_binary=True)
        self.add_composite_file('neostore.transaction.db.0', is_binary=True)


class Neo4jDBzip(Neo4j, Data):
    """Class for neo4jDB database files."""
    MetadataElement(name='reference_name', default='neostore_file', desc='Reference Name',
                    readonly=True, visible=True, set_in_upload=True, no_value='neostore')
    MetadataElement(name="neostore_zip", default=None, desc="Neostore zip",
                    readonly=True, visible=True, set_in_upload=True, no_value=None, optional=True)

    file_ext = "neostore.zip"
    composite_type = 'auto_primary_file'
    allow_datatype_change = False

    def __init__(self, **kwd):
        Data.__init__(self, **kwd)
        self.add_composite_file('%s.zip', description='neostore zip', substitute_name_with_metadata='reference_name',
                                is_binary=True)


if __name__ == '__main__':
    import doctest
    doctest.testmod(sys.modules[__name__])
