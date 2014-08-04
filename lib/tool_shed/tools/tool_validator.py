import filecmp
import logging
import os
import tempfile

from galaxy.tools import Tool
from galaxy.tools import parameters
from galaxy.tools.parameters import dynamic_options

from tool_shed.tools import data_table_manager

from tool_shed.util import basic_util
from tool_shed.util import hg_util
from tool_shed.util import shed_util_common as suc
from tool_shed.util import tool_util
from tool_shed.util import xml_util

log = logging.getLogger( __name__ )


class ToolValidator( object ):

    def __init__( self, app ):
        self.app = app
        self.tdtm = data_table_manager.ToolDataTableManager( self.app )

    def can_use_tool_config_disk_file( self, repository, repo, file_path, changeset_revision ):
        """
        Determine if repository's tool config file on disk can be used.  This method
        is restricted to tool config files since, with the exception of tool config
        files, multiple files with the same name will likely be in various directories
        in the repository and we're comparing file names only (not relative paths).
        """
        if not file_path or not os.path.exists( file_path ):
            # The file no longer exists on disk, so it must have been deleted at some previous
            # point in the change log.
            return False
        if changeset_revision == repository.tip( self.app ):
            return True
        file_name = basic_util.strip_path( file_path )
        latest_version_of_file = \
            self.get_latest_tool_config_revision_from_repository_manifest( repo, file_name, changeset_revision )
        can_use_disk_file = filecmp.cmp( file_path, latest_version_of_file )
        try:
            os.unlink( latest_version_of_file )
        except:
            pass
        return can_use_disk_file

    def check_tool_input_params( self, repo_dir, tool_config_name, tool, sample_files ):
        """
        Check all of the tool's input parameters, looking for any that are dynamically
        generated using external data files to make sure the files exist.
        """
        invalid_files_and_errors_tups = []
        correction_msg = ''
        for input_param in tool.input_params:
            if isinstance( input_param, parameters.basic.SelectToolParameter ) and input_param.is_dynamic:
                # If the tool refers to .loc files or requires an entry in the tool_data_table_conf.xml,
                # make sure all requirements exist.
                options = input_param.dynamic_options or input_param.options
                if options and isinstance( options, dynamic_options.DynamicOptions ):
                    if options.tool_data_table or options.missing_tool_data_table_name:
                        # Make sure the repository contains a tool_data_table_conf.xml.sample file.
                        sample_tool_data_table_conf = hg_util.get_config_from_disk( 'tool_data_table_conf.xml.sample', repo_dir )
                        if sample_tool_data_table_conf:
                            error, correction_msg = \
                                self.tdtm.handle_sample_tool_data_table_conf_file( sample_tool_data_table_conf,
                                                                                   persist=False )
                            if error:
                                invalid_files_and_errors_tups.append( ( 'tool_data_table_conf.xml.sample', correction_msg ) )
                            else:
                                options.missing_tool_data_table_name = None
                        else:
                            correction_msg = "This file requires an entry in the tool_data_table_conf.xml file.  "
                            correction_msg += "Upload a file named tool_data_table_conf.xml.sample to the repository "
                            correction_msg += "that includes the required entry to correct this error.<br/>"
                            invalid_tup = ( tool_config_name, correction_msg )
                            if invalid_tup not in invalid_files_and_errors_tups:
                                invalid_files_and_errors_tups.append( invalid_tup )
                    if options.index_file or options.missing_index_file:
                        # Make sure the repository contains the required xxx.loc.sample file.
                        index_file = options.index_file or options.missing_index_file
                        index_file_name = basic_util.strip_path( index_file )
                        sample_found = False
                        for sample_file in sample_files:
                            sample_file_name = basic_util.strip_path( sample_file )
                            if sample_file_name == '%s.sample' % index_file_name:
                                options.index_file = index_file_name
                                options.missing_index_file = None
                                if options.tool_data_table:
                                    options.tool_data_table.missing_index_file = None
                                sample_found = True
                                break
                        if not sample_found:
                            correction_msg = "This file refers to a file named <b>%s</b>.  " % str( index_file_name )
                            correction_msg += "Upload a file named <b>%s.sample</b> to the repository to correct this error." % \
                                str( index_file_name )
                            invalid_files_and_errors_tups.append( ( tool_config_name, correction_msg ) )
        return invalid_files_and_errors_tups

    def concat_messages( self, msg1, msg2 ):
        if msg1:
            if msg2:
                message = '%s  %s' % ( msg1, msg2 )
            else:
                message = msg1
        elif msg2:
            message = msg2
        else:
            message = ''
        return message

    def copy_disk_sample_files_to_dir( self, repo_files_dir, dest_path ):
        """
        Copy all files currently on disk that end with the .sample extension to the
        directory to which dest_path refers.
        """
        sample_files = []
        for root, dirs, files in os.walk( repo_files_dir ):
            if root.find( '.hg' ) < 0:
                for name in files:
                    if name.endswith( '.sample' ):
                        relative_path = os.path.join( root, name )
                        tool_util.copy_sample_file( self.app, relative_path, dest_path=dest_path )
                        sample_files.append( name )
        return sample_files

    def get_latest_tool_config_revision_from_repository_manifest( self, repo, filename, changeset_revision ):
        """
        Get the latest revision of a tool config file named filename from the repository
        manifest up to the value of changeset_revision.  This method is restricted to tool_config
        files rather than any file since it is likely that, with the exception of tool config
        files, multiple files will have the same name in various directories within the repository.
        """
        stripped_filename = basic_util.strip_path( filename )
        for changeset in hg_util.reversed_upper_bounded_changelog( repo, changeset_revision ):
            manifest_ctx = repo.changectx( changeset )
            for ctx_file in manifest_ctx.files():
                ctx_file_name = basic_util.strip_path( ctx_file )
                if ctx_file_name == stripped_filename:
                    try:
                        fctx = manifest_ctx[ ctx_file ]
                    except LookupError:
                        # The ctx_file may have been moved in the change set.  For example,
                        # 'ncbi_blastp_wrapper.xml' was moved to 'tools/ncbi_blast_plus/ncbi_blastp_wrapper.xml',
                        # so keep looking for the file until we find the new location.
                        continue
                    fh = tempfile.NamedTemporaryFile( 'wb', prefix="tmp-toolshed-gltcrfrm" )
                    tmp_filename = fh.name
                    fh.close()
                    fh = open( tmp_filename, 'wb' )
                    fh.write( fctx.data() )
                    fh.close()
                    return tmp_filename
        return None

    def get_list_of_copied_sample_files( self, repo, ctx, dir ):
        """
        Find all sample files (files in the repository with the special .sample extension)
        in the reversed repository manifest up to ctx.  Copy each discovered file to dir and
        return the list of filenames.  If a .sample file was added in a changeset and then
        deleted in a later changeset, it will be returned in the deleted_sample_files list.
        The caller will set the value of app.config.tool_data_path to dir in order to load
        the tools and generate metadata for them.
        """
        deleted_sample_files = []
        sample_files = []
        for changeset in hg_util.reversed_upper_bounded_changelog( repo, ctx ):
            changeset_ctx = repo.changectx( changeset )
            for ctx_file in changeset_ctx.files():
                ctx_file_name = basic_util.strip_path( ctx_file )
                # If we decide in the future that files deleted later in the changelog should
                # not be used, we can use the following if statement. if ctx_file_name.endswith( '.sample' )
                # and ctx_file_name not in sample_files and ctx_file_name not in deleted_sample_files:
                if ctx_file_name.endswith( '.sample' ) and ctx_file_name not in sample_files:
                    fctx = hg_util.get_file_context_from_ctx( changeset_ctx, ctx_file )
                    if fctx in [ 'DELETED' ]:
                        # Since the possibly future used if statement above is commented out, the
                        # same file that was initially added will be discovered in an earlier changeset
                        # in the change log and fall through to the else block below.  In other words,
                        # if a file named blast2go.loc.sample was added in change set 0 and then deleted
                        # in changeset 3, the deleted file in changeset 3 will be handled here, but the
                        # later discovered file in changeset 0 will be handled in the else block below.
                        # In this way, the file contents will always be found for future tools even though
                        # the file was deleted.
                        if ctx_file_name not in deleted_sample_files:
                            deleted_sample_files.append( ctx_file_name )
                    else:
                        sample_files.append( ctx_file_name )
                        tmp_ctx_file_name = os.path.join( dir, ctx_file_name.replace( '.sample', '' ) )
                        fh = open( tmp_ctx_file_name, 'wb' )
                        fh.write( fctx.data() )
                        fh.close()
        return sample_files, deleted_sample_files

    def handle_sample_files_and_load_tool_from_disk( self, repo_files_dir, repository_id, tool_config_filepath, work_dir ):
        """
        Copy all sample files from disk to a temporary directory since the sample files may
        be in multiple directories.
        """
        message = ''
        sample_files = self.copy_disk_sample_files_to_dir( repo_files_dir, work_dir )
        if sample_files:
            if 'tool_data_table_conf.xml.sample' in sample_files:
                # Load entries into the tool_data_tables if the tool requires them.
                tool_data_table_config = os.path.join( work_dir, 'tool_data_table_conf.xml' )
                error, message = self.tdtm.handle_sample_tool_data_table_conf_file( tool_data_table_config,
                                                                                    persist=False )
        tool, valid, message2 = self.load_tool_from_config( repository_id, tool_config_filepath )
        message = self.concat_messages( message, message2 )
        return tool, valid, message, sample_files

    def handle_sample_files_and_load_tool_from_tmp_config( self, repo, repository_id, changeset_revision,
                                                           tool_config_filename, work_dir ):
        tool = None
        message = ''
        ctx = hg_util.get_changectx_for_changeset( repo, changeset_revision )
        # We're not currently doing anything with the returned list of deleted_sample_files here.  It is
        # intended to help handle sample files that are in the manifest, but have been deleted from disk.
        sample_files, deleted_sample_files = self.get_list_of_copied_sample_files( repo, ctx, dir=work_dir )
        if sample_files:
            self.app.config.tool_data_path = work_dir
            if 'tool_data_table_conf.xml.sample' in sample_files:
                # Load entries into the tool_data_tables if the tool requires them.
                tool_data_table_config = os.path.join( work_dir, 'tool_data_table_conf.xml' )
                if tool_data_table_config:
                    error, message = self.tdtm.handle_sample_tool_data_table_conf_file( tool_data_table_config,
                                                                                        persist=False )
                    if error:
                        log.debug( message )
        manifest_ctx, ctx_file = hg_util.get_ctx_file_path_from_manifest( tool_config_filename, repo, changeset_revision )
        if manifest_ctx and ctx_file:
            tool, message2 = self.load_tool_from_tmp_config( repo, repository_id, manifest_ctx, ctx_file, work_dir )
            message = self.concat_messages( message, message2 )
        return tool, message, sample_files

    def load_tool_from_changeset_revision( self, repository_id, changeset_revision, tool_config_filename ):
        """
        Return a loaded tool whose tool config file name (e.g., filtering.xml) is the value
        of tool_config_filename.  The value of changeset_revision is a valid (downloadable)
        changeset revision.  The tool config will be located in the repository manifest between
        the received valid changeset revision and the first changeset revision in the repository,
        searching backwards.
        """
        original_tool_data_path = self.app.config.tool_data_path
        repository = suc.get_repository_in_tool_shed( self.app, repository_id )
        repo_files_dir = repository.repo_path( self.app )
        repo = hg_util.get_repo_for_repository( self.app, repository=None, repo_path=repo_files_dir, create=False )
        message = ''
        tool = None
        can_use_disk_file = False
        tool_config_filepath = suc.get_absolute_path_to_file_in_repository( repo_files_dir, tool_config_filename )
        work_dir = tempfile.mkdtemp( prefix="tmp-toolshed-ltfcr" )
        can_use_disk_file = self.can_use_tool_config_disk_file( repository,
                                                                repo,
                                                                tool_config_filepath,
                                                                changeset_revision )
        if can_use_disk_file:
            self.app.config.tool_data_path = work_dir
            tool, valid, message, sample_files = \
                self.handle_sample_files_and_load_tool_from_disk( repo_files_dir,
                                                                  repository_id,
                                                                  tool_config_filepath,
                                                                  work_dir )
            if tool is not None:
                invalid_files_and_errors_tups = \
                    self.check_tool_input_params( repo_files_dir,
                                                  tool_config_filename,
                                                  tool,
                                                  sample_files )
                if invalid_files_and_errors_tups:
                    message2 = tool_util.generate_message_for_invalid_tools( self.app,
                                                                             invalid_files_and_errors_tups,
                                                                             repository,
                                                                             metadata_dict=None,
                                                                             as_html=True,
                                                                             displaying_invalid_tool=True )
                    message = self.concat_messages( message, message2 )
        else:
            tool, message, sample_files = \
                self.handle_sample_files_and_load_tool_from_tmp_config( repo,
                                                                        repository_id,
                                                                        changeset_revision,
                                                                        tool_config_filename,
                                                                        work_dir )
        basic_util.remove_dir( work_dir )
        self.app.config.tool_data_path = original_tool_data_path
        # Reset the tool_data_tables by loading the empty tool_data_table_conf.xml file.
        self.tdtm.reset_tool_data_tables()
        return repository, tool, message

    def load_tool_from_config( self, repository_id, full_path ):
        try:
            tool = self.app.toolbox.load_tool( full_path, repository_id=repository_id )
            valid = True
            error_message = None
        except KeyError, e:
            tool = None
            valid = False
            error_message = 'This file requires an entry for "%s" in the tool_data_table_conf.xml file.  Upload a file ' % str( e )
            error_message += 'named tool_data_table_conf.xml.sample to the repository that includes the required entry to correct '
            error_message += 'this error.  '
        except Exception, e:
            tool = None
            valid = False
            error_message = str( e )
        return tool, valid, error_message

    def load_tool_from_tmp_config( self, repo, repository_id, ctx, ctx_file, work_dir ):
        tool = None
        message = ''
        tmp_tool_config = hg_util.get_named_tmpfile_from_ctx( ctx, ctx_file, work_dir )
        if tmp_tool_config:
            tool_element, error_message = xml_util.parse_xml( tmp_tool_config )
            if tool_element is None:
                return tool, message
            # Look for external files required by the tool config.
            tmp_code_files = []
            external_paths = Tool.get_externally_referenced_paths( tmp_tool_config )
            for path in external_paths:
                tmp_code_file_name = hg_util.copy_file_from_manifest( repo, ctx, path, work_dir )
                if tmp_code_file_name:
                    tmp_code_files.append( tmp_code_file_name )
            tool, valid, message = self.load_tool_from_config( repository_id, tmp_tool_config )
            for tmp_code_file in tmp_code_files:
                try:
                    os.unlink( tmp_code_file )
                except:
                    pass
            try:
                os.unlink( tmp_tool_config )
            except:
                pass
        return tool, message
