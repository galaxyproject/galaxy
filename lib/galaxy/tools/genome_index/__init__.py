from __future__ import with_statement

import os, shutil, logging, tempfile, tarfile

from galaxy import model, util
from galaxy.web.framework.helpers import to_unicode
from galaxy.model.item_attrs import UsesAnnotations
from galaxy.util.json import *
from galaxy.web.base.controller import UsesHistoryMixin
from galaxy.tools.data import ToolDataTableManager

import pkg_resources
pkg_resources.require("simplejson")
import simplejson

log = logging.getLogger(__name__)

def load_genome_index_tools( toolbox ):
    """ Adds tools for indexing genomes via the main job runner. """
    # Create XML for loading the tool.
    tool_xml_text = """
        <tool id="__GENOME_INDEX__" name="Index Genome" version="0.1" tool_type="genome_index">
          <type class="GenomeIndexTool" module="galaxy.tools"/>
          <action module="galaxy.tools.actions.index_genome" class="GenomeIndexToolAction"/>
          <command>$__GENOME_INDEX_COMMAND__ $output_file $output_file.files_path "$__app__.config.rsync_url" "$__app__.config.tool_data_path"</command>
          <inputs>
            <param name="__GENOME_INDEX_COMMAND__" type="hidden"/>
          </inputs>
          <outputs>
            <data format="txt" name="output_file"/>
          </outputs>
          <stdio>
            <exit_code range="1:" err_level="fatal" />
          </stdio>
        </tool>
        """
        
    # Load index tool.
    tmp_name = tempfile.NamedTemporaryFile()
    tmp_name.write( tool_xml_text )
    tmp_name.flush()
    genome_index_tool = toolbox.load_tool( tmp_name.name )
    toolbox.tools_by_id[ genome_index_tool.id ] = genome_index_tool
    log.debug( "Loaded genome index tool: %s", genome_index_tool.id )
    
class GenomeIndexToolWrapper( object ):
    """ Provides support for performing jobs that index a genome. """
    def __init__( self, job_id ):
        self.locations = dict()
        self.job_id = job_id
        
    def setup_job( self, genobj ):
        """ Perform setup for job to index a genome and return an archive. Method generates 
            attribute files, sets the corresponding attributes in the associated database
            object, and returns a command line for running the job. The command line
            includes the command, inputs, and options; it does not include the output 
            file because it must be set at runtime. """
        
        #
        # Create and return command line for running tool.
        #
        scriptpath = os.path.join( os.path.abspath( os.getcwd() ), "lib/galaxy/tools/genome_index/index_genome.py" )
        return "python %s %s %s" % ( scriptpath, genobj.indexer, genobj.fasta_path )
        
    def postprocessing( self, sa_session, app ):
        """ Finish the job, move the finished indexes to their final resting place,
            and update the .loc files where applicable. """
        gitd = sa_session.query( model.GenomeIndexToolData ).filter_by( job_id=self.job_id ).first()
        indexdirs = dict( bfast='bfast_index', bowtie='bowtie_index', bowtie2='bowtie2_index', 
                          bwa='bwa_index', perm='perm_%s_index', picard='srma_index', sam='sam_index' )
        

        if gitd:
            fp = open( gitd.dataset.get_file_name(), 'r' )
            deferred = sa_session.query( model.DeferredJob ).filter_by( id=gitd.deferred_job_id ).first()
            try:
                logloc = simplejson.load( fp )
            except ValueError:
                deferred.state = app.model.DeferredJob.states.ERROR
                sa_session.add( deferred )
                sa_session.flush()
                log.debug( 'Indexing job failed, setting deferred job state to error.' )
                return False
            finally:
                fp.close()
            destination = None
            tdtman = ToolDataTableManager( app.config.tool_data_path )
            xmltree = tdtman.load_from_config_file( app.config.tool_data_table_config_path, app.config.tool_data_path )
            for node in xmltree:
                table = node.get('name')
                location = node.findall('file')[0].get('path')
                self.locations[table] = os.path.abspath( location )
            locbase = os.path.abspath( os.path.split( self.locations['all_fasta'] )[0] )
            params = deferred.params
            dbkey = params[ 'dbkey' ]
            basepath = os.path.join( os.path.abspath( app.config.genome_data_path ), dbkey )
            intname = params[ 'intname' ]
            indexer = gitd.indexer
            workingdir = os.path.abspath( gitd.dataset.extra_files_path )
            location = []
            indexdata = gitd.dataset.extra_files_path
            if indexer == '2bit':
                indexdata = os.path.join( workingdir, '%s.2bit' % dbkey )
                destination = os.path.join( basepath, 'seq', '%s.2bit' % dbkey )
                location.append( dict( line='\t'.join( [ 'seq', dbkey, destination ] ), file= os.path.join( locbase, 'alignseq.loc' ) ) )
            elif indexer == 'bowtie':
                self._ex_tar( workingdir, 'cs.tar' )
                destination = os.path.join( basepath, 'bowtie_index' )
                for var in [ 'nt', 'cs' ]:
                    for line in logloc[ var ]:
                        idx = line
                        if var == 'nt':
                            locfile = self.locations[ 'bowtie_indexes' ]
                            locdir = os.path.join( destination, idx )
                        else:
                            locfile = self.locations[ 'bowtie_indexes_color' ]
                            locdir = os.path.join( destination, var, idx )
                        location.append( dict( line='\t'.join( [ dbkey, dbkey, intname, locdir ] ), file=locfile ) )
            elif indexer == 'bowtie2':
                destination = os.path.join( basepath, 'bowtie2_index' )
                for line in logloc[ 'nt' ]:
                    idx = line
                    locfile = self.locations[ 'bowtie2_indexes' ]
                    locdir = os.path.join( destination, idx )
                    location.append( dict( line='\t'.join( [ dbkey, dbkey, intname, locdir ] ), file=locfile ) )
            elif indexer == 'bwa':
                self._ex_tar( workingdir, 'cs.tar' )
                destination = os.path.join( basepath, 'bwa_index' )
                for var in [ 'nt', 'cs' ]:
                    for line in logloc[ var ]:
                        idx = line
                        if var == 'nt':
                            locfile = self.locations[ 'bwa_indexes' ]
                            locdir = os.path.join( destination, idx )
                        else:
                            locfile = self.locations[ 'bwa_indexes_color' ]
                            locdir = os.path.join( destination, var, idx )
                        location.append( dict( line='\t'.join( [ dbkey, dbkey, intname, locdir ] ), file=locfile ) )
            elif indexer == 'perm':
                self._ex_tar( workingdir, 'cs.tar' )
                destination = os.path.join( basepath, 'perm_index' )
                for var in [ 'nt', 'cs' ]:
                    for line in logloc[ var ]:
                        idx = line.pop()
                        if var == 'nt':
                            locfile = self.locations[ 'perm_base_indexes' ]
                            locdir = os.path.join( destination, idx )
                        else:
                            locfile = self.locations[ 'perm_color_indexes' ]
                            locdir = os.path.join( destination, var, idx )
                        line.append( locdir )
                        location.append( dict( line='\t'.join( line ), file=locfile ) )
            elif indexer == 'picard':
                destination = os.path.join( basepath, 'srma_index' )
                for var in [ 'nt' ]:
                    for line in logloc[ var ]:
                        idx = line
                        locfile = self.locations[ 'picard_indexes' ]
                        locdir = os.path.join( destination, idx )
                        location.append( dict( line='\t'.join( [ dbkey, dbkey, intname, locdir ] ), file=locfile ) )
            elif indexer == 'sam':
                destination = os.path.join( basepath, 'sam_index' )
                for var in [ 'nt' ]:
                    for line in logloc[ var ]:
                        locfile = self.locations[ 'sam_fa_indexes' ]
                        locdir = os.path.join( destination, line )
                        location.append( dict( line='\t'.join( [ 'index', dbkey, locdir ] ), file=locfile ) )
            
            if destination is not None and os.path.exists( os.path.split( destination )[0] ) and not os.path.exists( destination ):
                log.debug( 'Moving %s to %s' % ( indexdata, destination ) )
                shutil.move( indexdata, destination )
                if indexer not in [ '2bit' ]:
                    genome = '%s.fa' % dbkey
                    target = os.path.join( destination, genome )
                    fasta = os.path.abspath( os.path.join( basepath, 'seq', genome ) )
                    self._check_link( fasta, target )
                    if os.path.exists( os.path.join( destination, 'cs' ) ):
                        target = os.path.join( destination, 'cs', genome )
                        fasta = os.path.abspath( os.path.join( basepath, 'seq', genome ) )
                        self._check_link( fasta, target )
            for line in location:
                self._add_line( line[ 'file' ], line[ 'line' ] )
            deferred.state = app.model.DeferredJob.states.OK
            sa_session.add( deferred )
            sa_session.flush()

        
    def _check_link( self, targetfile, symlink ):
        target = os.path.relpath( targetfile, os.path.dirname( symlink ) )
        filename = os.path.basename( targetfile )
        if not os.path.exists( targetfile ): # this should never happen.
            raise Exception, "%s not found. Unable to proceed without a FASTA file. Aborting." % targetfile
        if os.path.exists( symlink ) and os.path.islink( symlink ):
            if os.path.realpath( symlink ) == os.path.abspath( targetfile ): # symlink exists, points to the correct FASTA file.
                return
            else: # no it doesn't. Make a new one, and this time do it right.
                os.remove( symlink )
                os.symlink( target, symlink )
                return
        elif not os.path.exists( symlink ): # no symlink to the FASTA file. Create one.
            os.symlink( target, symlink )
            return
        elif os.path.exists( symlink ) and not os.path.islink( symlink ):
            if self._hash_file( targetfile ) == self._hash_file( symlink ): # files are identical. No need to panic.
                return
            else:
                if os.path.getsize( symlink ) == 0: # somehow an empty file got copied instead of the symlink. Delete with extreme prejudice.
                    os.remove( symlink )
                    os.symlink( target, symlink )
                    return
                else:
                    raise Exception, "Regular file %s exists, is not empty, contents do not match %s." % ( symlink, targetfile )
    
    def _hash_file( self, filename ):
        import hashlib
        md5 = hashlib.md5()
        with open( filename, 'rb' ) as f: 
            for chunk in iter( lambda: f.read( 8192 ), '' ):
                 md5.update( chunk )
        return md5.digest()

    
    def _ex_tar( self, directory, filename ):
        fh = tarfile.open( os.path.join( directory, filename ) )
        fh.extractall( path=directory )
        fh.close()
        os.remove( os.path.join( directory, filename ) )
        
    def _add_line( self, locfile, newline ):
        filepath = locfile
        origlines = []
        output = []
        comments = []
        with open( filepath, 'r' ) as destfile:
            for line in destfile:
                origlines.append( line.strip() )
        if newline not in origlines:
            origlines.append( newline )
            with open( filepath, 'w+' ) as destfile:
                origlines.append( '' )
                destfile.write( '\n'.join( origlines ) )
