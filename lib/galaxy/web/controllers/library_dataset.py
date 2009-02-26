import os, shutil, urllib, StringIO, re, gzip, tempfile, shutil, zipfile
from galaxy.web.base.controller import *
from galaxy import util, jobs
from galaxy.datatypes import sniff
from galaxy.security import RBACAgent

log = logging.getLogger( __name__ )

class UploadLibraryDataset( BaseController ):
    def remove_tempfile( self, filename ):
        try:
            os.unlink( filename )
        except:
            log.exception( 'failure removing temporary file: %s' % filename )
    def add_file( self, trans, folder_id, file_obj, name, file_format, dbkey, roles, info='no info', space_to_tab=False, replace_dataset=None ):
        folder = trans.app.model.LibraryFolder.get( folder_id )
        data_type = None
        temp_name = sniff.stream_to_file( file_obj )
        # See if we have an empty file
        if not os.path.getsize( temp_name ) > 0:
            raise BadFileException( "you attempted to upload an empty file." )
        # See if we have a gzipped file, which, if it passes our restrictions, we'll uncompress on the fly.
        is_gzipped, is_valid = self.check_gzip( temp_name )
        if is_gzipped and not is_valid:
            raise BadFileException( "you attempted to upload an inappropriate file." )
        elif is_gzipped and is_valid:
            # We need to uncompress the temp_name file
            CHUNK_SIZE = 2**20 # 1Mb   
            fd, uncompressed = tempfile.mkstemp()   
            gzipped_file = gzip.GzipFile( temp_name )
            while 1:
                try:
                    chunk = gzipped_file.read( CHUNK_SIZE )
                except IOError:
                    os.close( fd )
                    os.remove( uncompressed )
                    raise BadFileException( 'problem uncompressing gzipped data.' )
                if not chunk:
                    break
                os.write( fd, chunk )
            os.close( fd )
            gzipped_file.close()
            # Replace the gzipped file with the decompressed file
            shutil.move( uncompressed, temp_name )
            name = name.rstrip( '.gz' )
            data_type = 'gzip'
        if not data_type:
            # See if we have a zip archive
            is_zipped, is_valid, test_ext = self.check_zip( temp_name )
            if is_zipped and not is_valid:
                raise BadFileException( "you attempted to upload an inappropriate file." )
            elif is_zipped and is_valid:
                # Currently, we force specific tools to handle this case.  We also require the user
                # to manually set the incoming file_format
                if ( test_ext == 'ab1' or test_ext == 'scf' ) and file_format != 'binseq.zip':
                    raise BadFileException( "Invalid 'File Format' for archive consisting of binary files - use 'Binseq.zip'." )
                elif test_ext == 'txt' and file_format != 'txtseq.zip':
                    raise BadFileException( "Invalid 'File Format' for archive consisting of text files - use 'Txtseq.zip'." )
                if not ( file_format == 'binseq.zip' or file_format == 'txtseq.zip' ):
                    raise BadFileException( "you must manually set the 'File Format' to either 'Binseq.zip' or 'Txtseq.zip' when uploading zip files." )
                data_type = 'zip'
                ext = file_format
        if not data_type:
            if self.check_binary( temp_name ):
                ext = file_name.split( "." )[1].strip().lower()
                if not( ext == 'ab1' or ext == 'scf' ):
                    raise BadFileException( "you attempted to upload an inappropriate file." )
                if ext == 'ab1' and file_format != 'ab1':
                    raise BadFileException( "you must manually set the 'File Format' to 'Ab1' when uploading ab1 files." )
                elif ext == 'scf' and file_format != 'scf':
                    raise BadFileException( "you must manually set the 'File Format' to 'Scf' when uploading scf files." )
                data_type = 'binary'
        if not data_type:
            # We must have a text file
            if self.check_html( temp_name ):
                raise BadFileException( "you attempted to upload an inappropriate file." )
        if data_type != 'binary' and data_type != 'zip':
            if space_to_tab:
                self.line_count = sniff.convert_newlines_sep2tabs( temp_name )
            elif os.stat( temp_name ).st_size < 262144000: # 250MB
                line_count = sniff.convert_newlines( temp_name )
            else:
                if sniff.check_newlines( temp_name ):
                    line_count = sniff.convert_newlines( temp_name )
                else:
                    line_count = None
            if file_format == 'auto':
                ext = sniff.guess_ext( temp_name, sniff_order=trans.app.datatypes_registry.sniff_order )    
            else:
                ext = file_format
            data_type = ext
        if info is None:
            info = 'uploaded %s file' % data_type
        if file_format == 'auto':
            data_type = sniff.guess_ext( temp_name, sniff_order=trans.app.datatypes_registry.sniff_order )    
        else:
            data_type = file_format
        if replace_dataset:
            # The replace_dataset param ( when not None ) refers to a LibraryDataset that is being replaced with a new version.
            # In this case, all of the permissions on the expired LibraryDataset will be applied to the new version.
            library_dataset = replace_dataset
        else:
            # If replace_dataset is None, the Library level permissions will be taken from the folder and applied to the new 
            # LibraryDataset, and the current user's DefaultUserPermissions will be applied to the associated Dataset.
            library_dataset = trans.app.model.LibraryDataset( folder=folder, name=name, info=info )
            library_dataset.flush()
            trans.app.security_agent.copy_library_permissions( folder, library_dataset )
        ldda = trans.app.model.LibraryDatasetDatasetAssociation( name=name, 
                                                                 info=info, 
                                                                 extension=data_type, 
                                                                 dbkey=dbkey, 
                                                                 library_dataset=library_dataset,
                                                                 create_dataset=True )
        ldda.flush()
        # Permissions must be the same on the LibraryDatasetDatasetAssociation and the associated LibraryDataset
        trans.app.security_agent.copy_library_permissions( library_dataset, ldda )
        if replace_dataset:
            # Copy the Dataset level permissions from replace_dataset to the new LibraryDatasetDatasetAssociation.dataset
            trans.app.security_agent.copy_dataset_permissions( replace_dataset.library_dataset_dataset_association.dataset, ldda.dataset )
        else:
            # Copy the current user's DefaultUserPermissions to the new LibraryDatasetDatasetAssociation.dataset
            trans.app.security_agent.set_all_dataset_permissions( ldda.dataset, trans.app.security_agent.user_get_default_permissions( trans.get_user() ) )
            folder.add_library_dataset( library_dataset, genome_build=dbkey )
        library_dataset.library_dataset_dataset_association_id = ldda.id
        library_dataset.flush()
        # If roles were selected upon upload, restrict access to the Dataset to those roles
        if roles:
            for role in roles:
                dp = trans.app.model.DatasetPermissions( RBACAgent.permitted_actions.DATASET_ACCESS.action, ldda.dataset, role )
                dp.flush()
        shutil.move( temp_name, ldda.dataset.file_name )
        ldda.dataset.state = ldda.dataset.states.OK
        ldda.init_meta()
        if line_count is not None:
            try:
                ldda.set_peek( line_count=line_count )
            except:
                ldda.set_peek()
        else:
            ldda.set_peek()
        ldda.set_size()
        if ldda.missing_meta():
            ldda.datatype.set_meta( ldda )
        ldda.flush()
        return ldda
    @web.expose
    def upload_dataset( self, trans, controller, library_id, folder_id, replace_dataset=None, **kwd ):
        # This method is called from both the admin and library controllers.  The replace_dataset param ( when
        # not None ) refers to a LibraryDataset that is being replaced with a new version.
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        dbkey = params.get( 'dbkey', '?' )
        file_format = params.get( 'file_format', 'auto' )
        data_file = params.get( 'file_data', '' )
        url_paste = params.get( 'url_paste', '' )
        server_dir = params.get( 'server_dir', 'None' )
        if replace_dataset is not None:
            replace_id = replace_dataset.id
        else:
            replace_id = None
        if data_file == '' and url_paste == '' and server_dir in [ 'None', '' ]:
            if trans.app.config.library_import_dir is not None:
                msg = 'Select a file, enter a URL or Text, or select a server directory.'
            else:
                msg = 'Select a file, enter a URL or enter Text.'
            trans.response.send_redirect( web.url_for( controller=controller,
                                                       action='library_dataset_dataset_association',
                                                       library_id=library_id,
                                                       folder_id=folder_id,
                                                       replace_id=replace_id, 
                                                       msg=util.sanitize_text( msg ),
                                                       messagetype='done' ) )
        space_to_tab = params.get( 'space_to_tab', False )
        if space_to_tab and space_to_tab not in [ "None", None ]:
            space_to_tab = True
        roles = []
        for role_id in util.listify( params.get( 'roles', [] ) ):
            roles.append( trans.app.model.Role.get( role_id ) )
        data_list = []
        created_ldda_ids = ''
        if 'filename' in dir( data_file ):
            file_name = data_file.filename
            file_name = file_name.split( '\\' )[-1]
            file_name = file_name.split( '/' )[-1]
            try:
                created_ldda = self.add_file( trans,
                                              folder_id,
                                              data_file.file,
                                              file_name,
                                              file_format,
                                              dbkey,
                                              roles,
                                              info="uploaded file",
                                              space_to_tab=space_to_tab,
                                              replace_dataset=replace_dataset )
                created_ldda_ids = str( created_ldda.id )
            except Exception, e:
                log.exception( 'exception in upload_dataset using file_name %s: %s' % ( str( file_name ), str( e ) ) )
                return self.upload_empty( trans, controller, library_id, "Error:", str( e ) )
        elif url_paste not in [ None, "" ]:
            if url_paste.lower().find( 'http://' ) >= 0 or url_paste.lower().find( 'ftp://' ) >= 0:
                url_paste = url_paste.replace( '\r', '' ).split( '\n' )
                for line in url_paste:
                    line = line.rstrip( '\r\n' )
                    if line:
                        try:
                            created_ldda = self.add_file( trans,
                                                          folder_id,
                                                          urllib.urlopen( line ),
                                                          line,
                                                          file_format,
                                                          dbkey,
                                                          roles,
                                                          info="uploaded url",
                                                          space_to_tab=space_to_tab,
                                                          replace_dataset=replace_dataset )
                            created_ldda_ids = '%s,%s' % ( created_ldda_ids, str( created_ldda.id ) )
                        except Exception, e:
                            log.exception( 'exception in upload_dataset using url_paste %s' % str( e ) )
                            return self.upload_empty( trans, controller, library_id, "Error:", str( e ) )
            else:
                is_valid = False
                for line in url_paste:
                    line = line.rstrip( '\r\n' )
                    if line:
                        is_valid = True
                        break
                if is_valid:
                    try:
                        created_ldda = self.add_file( trans,
                                                      folder_id,
                                                      StringIO.StringIO( url_paste ),
                                                      'Pasted Entry',
                                                      file_format,
                                                      dbkey,
                                                      roles,
                                                      info="pasted entry",
                                                      space_to_tab=space_to_tab,
                                                      replace_dataset=replace_dataset )
                        created_ldda_ids = '%s,%s' % ( created_ldda_ids, str( created_ldda.id ) )
                    except Exception, e:
                        log.exception( 'exception in add_file using StringIO.StringIO( url_paste ) %s' % str( e ) )
                        return self.upload_empty( trans, controller, library_id, "Error:", str( e ) )
        elif server_dir not in [ None, "", "None" ]:
            full_dir = os.path.join( trans.app.config.library_import_dir, server_dir )
            try:
                files = os.listdir( full_dir )
            except:
                log.debug( "Unable to get file list for %s" % full_dir )
            for file in files:
                full_file = os.path.join( full_dir, file )
                if not os.path.isfile( full_file ):
                    continue
                try:
                    created_ldda = self.add_file( trans,
                                                  folder_id,
                                                  open( full_file, 'rb' ),
                                                  file,
                                                  file_format,
                                                  dbkey,
                                                  roles,
                                                  info="imported file",
                                                  space_to_tab=space_to_tab,
                                                  replace_dataset=replace_dataset )
                    created_ldda_ids = '%s,%s' % ( created_ldda_ids, str( created_ldda.id ) )
                except Exception, e:
                    log.exception( 'exception in add_file using server_dir %s' % str( e ) )
                    return self.upload_empty( trans, controller, library_id, "Error:", str( e ) )
        if created_ldda_ids:
            created_ldda_ids = created_ldda_ids.lstrip( ',' )
            return created_ldda_ids
        else:
            return ''
    def check_gzip( self, temp_name ):
        temp = open( temp_name, "U" )
        magic_check = temp.read( 2 )
        temp.close()
        if magic_check != util.gzip_magic:
            return ( False, False )
        CHUNK_SIZE = 2**15 # 32Kb
        gzipped_file = gzip.GzipFile( temp_name )
        chunk = gzipped_file.read( CHUNK_SIZE )
        gzipped_file.close()
        if self.check_html( temp_name, chunk=chunk ) or self.check_binary( temp_name, chunk=chunk ):
            return( True, False )
        return ( True, True )
    def check_zip( self, temp_name ):
        if not zipfile.is_zipfile( temp_name ):
            return ( False, False, None )
        zip_file = zipfile.ZipFile( temp_name, "r" )
        # Make sure the archive consists of valid files.  The current rules are:
        # 1. Archives can only include .ab1, .scf or .txt files
        # 2. All file file_formats within an archive must be the same
        name = zip_file.namelist()[0]
        test_ext = name.split( "." )[1].strip().lower()
        if not ( test_ext == 'scf' or test_ext == 'ab1' or test_ext == 'txt' ):
            return ( True, False, test_ext )
        for name in zip_file.namelist():
            ext = name.split( "." )[1].strip().lower()
            if ext != test_ext:
                return ( True, False, test_ext )
        return ( True, True, test_ext )
    def check_html( self, temp_name, chunk=None ):
        if chunk is None:
            temp = open(temp_name, "U")
        else:
            temp = chunk
        regexp1 = re.compile( "<A\s+[^>]*HREF[^>]+>", re.I )
        regexp2 = re.compile( "<IFRAME[^>]*>", re.I )
        regexp3 = re.compile( "<FRAMESET[^>]*>", re.I )
        regexp4 = re.compile( "<META[^>]*>", re.I )
        lineno = 0
        for line in temp:
            lineno += 1
            matches = regexp1.search( line ) or regexp2.search( line ) or regexp3.search( line ) or regexp4.search( line )
            if matches:
                if chunk is None:
                    temp.close()
                return True
            if lineno > 100:
                break
        if chunk is None:
            temp.close()
        return False
    def check_binary( self, temp_name, chunk=None ):
        if chunk is None:
            temp = open( temp_name, "U" )
        else:
            temp = chunk
        lineno = 0
        for line in temp:
            lineno += 1
            line = line.strip()
            if line:
                for char in line:
                    if ord( char ) > 128:
                        if chunk is None:
                            temp.close()
                        return True
            if lineno > 10:
                break
        if chunk is None:
            temp.close()
        return False
    def upload_empty( self, trans, controller, library_id, err_code, err_msg ):
        msg = err_code + err_msg
        return trans.response.send_redirect( web.url_for( controller=controller,
                                                          action='browse_library',
                                                          id=library_id,
                                                          msg=util.sanitize_text( msg ),
                                                          messagetype='error' ) )
class BadFileException( Exception ):
    pass
