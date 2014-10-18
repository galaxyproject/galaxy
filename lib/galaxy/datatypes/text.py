# -*- coding: utf-8 -*-
""" Clearing house for generic text datatypes that are not XML or tabular.
"""


from galaxy.datatypes.data import Text
from galaxy.datatypes.data import get_file_peek
from galaxy.datatypes.data import nice_size
from galaxy import util

import tempfile
import subprocess
import json
import os

import logging
log = logging.getLogger(__name__)


class Json( Text ):
    file_ext = "json"

    def set_peek( self, dataset, is_multi_byte=False ):
        if not dataset.dataset.purged:
            dataset.peek = get_file_peek( dataset.file_name, is_multi_byte=is_multi_byte )
            dataset.blurb = "JavaScript Object Notation (JSON)"
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disc'

    def sniff( self, filename ):
        """
            Try to load the string with the json module. If successful it's a json file.
        """
        return self._looks_like_json( filename )

    def _looks_like_json( self, filename ):
        # Pattern used by SequenceSplitLocations
        if os.path.getsize(filename) < 50000:
            # If the file is small enough - don't guess just check.
            try:
                json.load( open(filename, "r") )
                return True
            except Exception:
                return False
        else:
            with open(filename, "r") as fh:
                while True:
                    line = fh.readline()
                    line = line.strip()
                    if line:
                        # simple types are valid JSON as well - but would such a file
                        # be interesting as JSON in Galaxy?
                        return line.startswith("[") or line.startswith("{")
            return False

    def display_peek( self, dataset ):
        try:
            return dataset.peek
        except:
            return "JSON file (%s)" % ( nice_size( dataset.get_size() ) )


class Ipynb( Json ):
    file_ext = "ipynb"

    def set_peek( self, dataset, is_multi_byte=False ):
        if not dataset.dataset.purged:
            dataset.peek = get_file_peek( dataset.file_name, is_multi_byte=is_multi_byte )
            dataset.blurb = "IPython Notebook"
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disc'

    def sniff( self, filename ):
        """
            Try to load the string with the json module. If successful it's a json file.
        """
        if self._looks_like_json( filename ):
            try:
                ipynb = json.load( open(filename) )
                if ipynb.get('nbformat', False) is not False and ipynb.get('metadata', False):
                    return True
                else:
                    return False
            except:
                return False

    def display_data(self, trans, dataset, preview=False, filename=None, to_ext=None, chunk=None, **kwd):
        config = trans.app.config
        trust = getattr( config, 'trust_ipython_notebook_conversion', False )
        if trust:
            return self._display_data_trusted(trans, dataset, preview=preview, fileame=filename, to_ext=to_ext, chunk=chunk, **kwd)
        else:
            return super(Ipynb, self).display_data( trans, dataset, preview=preview, fileame=filename, to_ext=to_ext, chunk=chunk, **kwd )

    def _display_data_trusted(self, trans, dataset, preview=False, filename=None, to_ext=None, chunk=None, **kwd):
        preview = util.string_as_bool( preview )
        if chunk:
            return self.get_chunk(trans, dataset, chunk)
        elif to_ext or not preview:
            return self._serve_raw(trans, dataset, to_ext)
        else:
            ofile_handle = tempfile.NamedTemporaryFile(delete=False)
            ofilename = ofile_handle.name
            ofile_handle.close()
            try:
                cmd = 'ipython nbconvert --to html --template basic %s --output %s' % (dataset.file_name, ofilename)
                log.info("Calling command %s" % cmd)
                subprocess.call(cmd, shell=True)
                ofilename = '%s.html' % ofilename
            except:
                ofilename = dataset.file_name
                log.exception( 'Command "%s" failed. Could not convert the IPython Notebook to HTML, defaulting to plain text.' % cmd )
            return open( ofilename )

    def set_meta( self, dataset, **kwd ):
        """
        Set the number of models in dataset.
        """
        pass
