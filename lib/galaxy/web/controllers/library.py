from galaxy.web.base.controller import *
from galaxy.model.orm import *
import logging, tempfile, zipfile, tarfile, os, sys

if sys.version_info[:2] < ( 2, 6 ):
    zipfile.BadZipFile = zipfile.error
if sys.version_info[:2] < ( 2, 5 ):
    zipfile.LargeZipFile = zipfile.error

log = logging.getLogger( __name__ )

class Library( BaseController ):
    @web.expose
    def browse( self, trans, **kwd ):
        libraries = trans.app.model.Library.filter( trans.app.model.Library.table.c.deleted==False ) \
                                           .order_by( trans.app.model.Library.table.c.name ).all()
        return trans.fill_template( '/library/browser.mako', libraries=libraries, default_action=kwd.get( 'default_action', None ) )
    index = browse
    @web.expose
    def import_datasets( self, trans, import_ids=[], **kwd ):
        if not import_ids:
            return trans.show_error_message( "You must select at least one dataset" )
        if not isinstance( import_ids, list ):
            import_ids = [ import_ids ]
        p = util.Params( kwd )
        if not p.action:
            return trans.show_error_message( "You must select an action to perform on selected datasets" )
        if p.action == 'add':
            history = trans.get_history()
            for id in import_ids:
                dataset = trans.app.model.LibraryFolderDatasetAssociation.get( id ).to_history_dataset_association()
                history.add_dataset( dataset )
                dataset.flush()
            history.flush()
            return trans.show_ok_message( "%i dataset(s) have been imported in to your history" % len( import_ids ), refresh_frames=['history'] )
        else:
            # Can't use mkstemp - the file must not exist first
            try:
                tmpd = tempfile.mkdtemp()
                tmpf = os.path.join( tmpd, 'library_download.' + p.action )
                if p.action == 'zip':
                    try:
                        archive = zipfile.ZipFile( tmpf, 'w', zipfile.ZIP_DEFLATED, True )
                    except RuntimeError:
                        log.exception( "Compression error when opening zipfile for library download" )
                        return trans.show_error_message( "ZIP compression is not available in this Python, please notify an administrator" )
                    except (TypeError, zipfile.LargeZipFile):
                        # ZIP64 is only in Python2.5+.  Remove TypeError when 2.4 support is dropped
                        log.warning( 'Max zip file size is 2GB, ZIP64 not supported' )
                        archive = zipfile.ZipFile( tmpf, 'w', zipfile.ZIP_DEFLATED )
                    archive.add = lambda x, y: archive.write( x, y.encode('CP437') )
                elif p.action == 'tgz':
                    try:
                        archive = tarfile.open( tmpf, 'w:gz' )
                    except tarfile.CompressionError:
                        log.exception( "Compression error when opening tarfile for library download" )
                        return trans.show_error_message( "gzip compression is not available in this Python, please notify an administrator" )
                elif p.action == 'tbz':
                    try:
                        archive = tarfile.open( tmpf, 'w:bz2' )
                    except tarfile.CompressionError:
                        log.exception( "Compression error when opening tarfile for library download" )
                        return trans.show_error_message( "bzip2 compression is not available in this Python, please notify an administrator" )
            except (OSError, zipfile.BadZipFile, tarfile.ReadError):
                log.exception( "Unable to create archive for download" )
                return trans.show_error_message( "Unable to create archive for download, please report this error" )
            seen = []
            for id in import_ids:
                lfda = trans.app.model.LibraryFolderDatasetAssociation.get( id )
                if not lfda or not trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.DATASET_ACCESS, dataset = lfda.dataset ):
                    continue
                path = ""
                parent_folder = lfda.folder
                while parent_folder is not None:
                    path = os.path.join( parent_folder.name, path )
                    if parent_folder.parent is None:
                        path = os.path.join( parent_folder.library_root[0].name, path )
                    parent_folder = parent_folder.parent
                path += lfda.name
                while path in seen:
                    path += '_'
                seen.append( path )
                try:
                    archive.add( lfda.dataset.file_name, path )
                except IOError:
                    log.exception( "Unable to write to temporary library download archive" )
                    return trans.show_error_message( "Unable to create archive for download, please report this error" )
            archive.close()
            tmpfh = open( tmpf )
            # clean up now
            try:
                os.unlink( tmpf )
                os.rmdir( tmpd )
            except OSError:
                log.exception( "Unable to remove temporary library download archive and directory" )
                return trans.show_error_message( "Unable to create archive for download, please report this error" )
            trans.response.headers[ "Content-Disposition" ] = "attachment; filename=GalaxyLibraryFiles.%s" % kwd['action']
            return tmpfh
    @web.expose
    def download_dataset_from_folder(self, trans, id, **kwd):
        """Catches the dataset id and displays file contents as directed"""
        # id refers to a LibraryFolderDatasetAssociation object
        lfda = trans.app.model.LibraryFolderDatasetAssociation.get( id )
        dataset = trans.app.model.Dataset.get( lfda.dataset_id )
        if not dataset:
            msg = 'Invalid id %s received for file downlaod' % str( id )
            return trans.response.send_redirect( web.url_for( action='library_browser', msg=msg, messagetype='error' ) )
        mime = trans.app.datatypes_registry.get_mimetype_by_extension( lfda.extension.lower() )
        trans.response.set_content_type( mime )
        fStat = os.stat( lfda.file_name )
        trans.response.headers[ 'Content-Length' ] = int( fStat.st_size )
        valid_chars = '.,^_-()[]0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
        fname = lfda.name
        fname = ''.join( c in valid_chars and c or '_' for c in fname )[ 0:150 ]
        trans.response.headers[ "Content-Disposition" ] = "attachment; filename=GalaxyLibraryDataset-%s-[%s]" % ( str( id ), fname )
        try:
            return open( lfda.file_name )
        except: 
            msg = 'This dataset contains no content'
            return trans.response.send_redirect( web.url_for( action='library_browser', msg=msg, messagetype='error' ) )
