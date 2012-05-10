import os, shutil, logging, tempfile, json, tarfile
from galaxy import model, util
from galaxy.web.framework.helpers import to_unicode
from galaxy.model.item_attrs import UsesAnnotations
from galaxy.util.json import *
from galaxy.web.base.controller import UsesHistory
from galaxy.tools.data import ToolDataTableManager

log = logging.getLogger(__name__)

def load_genome_index_tools( toolbox ):
    """ Adds tools for indexing genomes via the main job runner. """
    # Use same process as that used in load_external_metadata_tool; see that 
    # method for why create tool description files on the fly.
    tool_xml_text = """
        <tool id="__GENOME_INDEX__" name="Index Genome" version="0.1" tool_type="genome_index">
          <type class="GenomeIndexTool" module="galaxy.tools"/>
          <action module="galaxy.tools.actions.index_genome" class="GenomeIndexToolAction"/>
          <command>$__GENOME_INDEX_COMMAND__ $output_file $output_file.files_path</command>
          <inputs>
            <param name="__GENOME_INDEX_COMMAND__" type="hidden"/>
          </inputs>
          <outputs>
            <data format="txt" name="output_file"/>
          </outputs>
        </tool>
        """
        
    # Load export tool.
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
            destination = None
            tdtman = ToolDataTableManager()
            xmltree = tdtman.load_from_config_file(app.config.tool_data_table_config_path)
            for node in xmltree:
                table = node.get('name')
                location = node.findall('file')[0].get('path')
                self.locations[table] = os.path.abspath( location )
            locbase = os.path.abspath( os.path.split( self.locations['all_fasta'] )[0] )
            deferred = sa_session.query( model.DeferredJob ).filter_by( id=gitd.deferred_job_id ).first()
            params = deferred.params
            dbkey = params[ 'dbkey' ]
            basepath = os.path.join( os.path.abspath( app.config.genome_data_path ), dbkey )
            intname = params[ 'intname' ]
            indexer = gitd.indexer
            workingdir = os.path.abspath( gitd.dataset.extra_files_path )
            fp = open( gitd.dataset.get_file_name(), 'r' )
            logloc = json.load( fp )
            fp.close()
            location = []
            indexdata = gitd.dataset.extra_files_path
            if indexer == '2bit':
                indexdata = os.path.join( workingdir, '%s.2bit' % dbkey )
                destination = os.path.join( basepath, 'seq', '%s.2bit' % dbkey )
                location.append( dict( line='\t'.join( [ 'seq', dbkey, os.path.join( destination, '%s.2bit' % dbkey ) ] ), file= os.path.join( locbase, 'alignseq.loc' ) ) )
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
                    genome = '%s.fa'
                    target = os.path.join( destination, genome )
                    farel = os.path.relpath( os.path.join( basepath, 'seq', genome ), destination )
                    os.symlink( farel, target )
                    if os.path.exists( os.path.join( destination, 'cs' ) ):
                        target = os.path.join( destination, 'cs', genome )
                        farel = os.path.relpath( os.path.join( basepath, 'seq', genome ), os.path.join( destination, 'cs' ) )
                        os.symlink( os.path.join( farel, target ) )
            for line in location:
                self._add_line( line[ 'file' ], line[ 'line' ] )
        
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
                destfile.write( '\n'.join( origlines ) )
