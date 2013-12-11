"""
API operations on the dataset from library.
"""
import glob
import logging
import operator
import os
import os.path
import string
import sys
import tarfile
import tempfile
import urllib
import urllib2
import zipfile
from galaxy.security import Action
from galaxy import util, web
from galaxy.util.streamball import StreamBall
from galaxy.web.base.controller import BaseAPIController, UsesLibraryMixinItems

import logging
log = logging.getLogger( __name__ )

class DatasetsController( BaseAPIController, UsesLibraryMixinItems ):

    @web.expose_api
    def show( self, trans, id, **kwd ):
        """
        GET /api/libraries/datasets/{encoded_dataset_id}
        Displays information about the dataset identified by the lda ID.
        """
        # Get dataset.
        try:
            dataset = self.get_library_dataset( trans, id = id )
        except Exception, e:
            return str( e )
        try:
            # Default: return dataset as dict.
            rval = dataset.to_dict()
        except Exception, e:
            rval = "Error in dataset API at listing contents: " + str( e )
            log.error( rval + ": %s" % str(e), exc_info=True )
            trans.response.status = 500

        rval['id'] = trans.security.encode_id(rval['id']);
        rval['ldda_id'] = trans.security.encode_id(rval['ldda_id']);
        rval['folder_id'] = 'f' + trans.security.encode_id(rval['folder_id'])

        return rval

    @web.expose
    def download( self, trans, format, **kwd ):
        """
        POST /api/libraries/datasets/download/{format}
        POST data: ldda_ids = []
        Downloads dataset(s) in the requested format.
        """
        lddas = []
#         is_admin = trans.user_is_admin()
#         current_user_roles = trans.get_current_user_roles()

        datasets_to_download = kwd['ldda_ids%5B%5D']

        if ( datasets_to_download != None ):
            datasets_to_download = util.listify( datasets_to_download )
            for dataset_id in datasets_to_download:
                try:
                    ldda = trans.sa_session.query( trans.app.model.LibraryDatasetDatasetAssociation ).get( trans.security.decode_id( dataset_id ) )
                    assert not ldda.dataset.purged
                    lddas.append( ldda )
                except:
                    ldda = None
                    message += "Invalid library dataset id (%s) specified.  " % str( dataset_id )

        if format in [ 'zip','tgz','tbz' ]:
                error = False
                killme = string.punctuation + string.whitespace
                trantab = string.maketrans(killme,'_'*len(killme))
                try:
                    outext = 'zip'
                    if format == 'zip':
                        # Can't use mkstemp - the file must not exist first
                        tmpd = tempfile.mkdtemp()
                        util.umask_fix_perms( tmpd, trans.app.config.umask, 0777, self.app.config.gid )
                        tmpf = os.path.join( tmpd, 'library_download.' + format )
                        if trans.app.config.upstream_gzip:
                            archive = zipfile.ZipFile( tmpf, 'w', zipfile.ZIP_STORED, True )
                        else:
                            archive = zipfile.ZipFile( tmpf, 'w', zipfile.ZIP_DEFLATED, True )
                        archive.add = lambda x, y: archive.write( x, y.encode('CP437') )
                    elif format == 'tgz':
                        if trans.app.config.upstream_gzip:
                            archive = StreamBall( 'w|' )
                            outext = 'tar'
                        else:
                            archive = StreamBall( 'w|gz' )
                            outext = 'tgz'
                    elif format == 'tbz':
                        archive = StreamBall( 'w|bz2' )
                        outext = 'tbz2'
                except ( OSError, zipfile.BadZipfile ):
                    error = True
                    log.exception( "Unable to create archive for download" )
                    message = "Unable to create archive for download, please report this error"
                    status = 'error'
                except:
                     error = True
                     log.exception( "Unexpected error %s in create archive for download" % sys.exc_info()[0] )
                     message = "Unable to create archive for download, please report - %s" % sys.exc_info()[0]
                     status = 'error'
                if not error:
                    composite_extensions = trans.app.datatypes_registry.get_composite_extensions()
                    seen = []
                    for ldda in lddas:
                        if ldda.dataset.state in [ 'new', 'upload', 'queued', 'running', 'empty', 'discarded' ]:
                            continue
                        ext = ldda.extension
                        is_composite = ext in composite_extensions
                        path = ""
                        parent_folder = ldda.library_dataset.folder
                        while parent_folder is not None:
                            # Exclude the now-hidden "root folder"
                            if parent_folder.parent is None:
                                path = os.path.join( parent_folder.library_root[0].name, path )
                                break
                            path = os.path.join( parent_folder.name, path )
                            parent_folder = parent_folder.parent
                        path += ldda.name
                        while path in seen:
                            path += '_'
                        seen.append( path )
                        zpath = os.path.split(path)[-1] # comes as base_name/fname
                        outfname,zpathext = os.path.splitext(zpath)
                        if is_composite:
                            # need to add all the components from the extra_files_path to the zip
                            if zpathext == '':
                                zpath = '%s.html' % zpath # fake the real nature of the html file
                            try:
                                archive.add(ldda.dataset.file_name,zpath) # add the primary of a composite set
                            except IOError:
                                error = True
                                log.exception( "Unable to add composite parent %s to temporary library download archive" % ldda.dataset.file_name)
                                message = "Unable to create archive for download, please report this error"
                                status = 'error'
                                continue
                            flist = glob.glob(os.path.join(ldda.dataset.extra_files_path,'*.*')) # glob returns full paths
                            for fpath in flist:
                                efp,fname = os.path.split(fpath)
                                if fname > '':
                                    fname = fname.translate(trantab)
                                try:
                                    archive.add( fpath,fname )
                                except IOError:
                                    error = True
                                    log.exception( "Unable to add %s to temporary library download archive %s" % (fname,outfname))
                                    message = "Unable to create archive for download, please report this error"
                                    status = 'error'
                                    continue
                        else: # simple case
                            try:
                                archive.add( ldda.dataset.file_name, path )
                            except IOError:
                                error = True
                                log.exception( "Unable to write %s to temporary library download archive" % ldda.dataset.file_name)
                                message = "Unable to create archive for download, please report this error"
                                status = 'error'
                    if not error:
                        lname = 'selected_dataset'
                        fname = lname.replace( ' ', '_' ) + '_files'
                        if format == 'zip':
                            archive.close()
                            trans.response.set_content_type( "application/octet-stream" )
                            trans.response.headers[ "Content-Disposition" ] = 'attachment; filename="%s.%s"' % (fname,outext)
                            archive = util.streamball.ZipBall(tmpf, tmpd)
                            archive.wsgi_status = trans.response.wsgi_status()
                            archive.wsgi_headeritems = trans.response.wsgi_headeritems()
                            return archive.stream
                        else:
                            trans.response.set_content_type( "application/x-tar" )
                            trans.response.headers[ "Content-Disposition" ] = 'attachment; filename="%s.%s"' % (fname,outext)
                            archive.wsgi_status = trans.response.wsgi_status()
                            archive.wsgi_headeritems = trans.response.wsgi_headeritems()
                            return archive.stream
        elif format == 'uncompressed':
            if len(lddas) != 1:
                return 'Wrong request'
            else:
                single_dataset = lddas[0]
                trans.response.set_content_type( single_dataset.get_mime() )
                fStat = os.stat( ldda.file_name )
                trans.response.headers[ 'Content-Length' ] = int( fStat.st_size )
                valid_chars = '.,^_-()[]0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
                fname = ldda.name
                fname = ''.join( c in valid_chars and c or '_' for c in fname )[ 0:150 ]
                trans.response.headers[ "Content-Disposition" ] = 'attachment; filename="%s"' % fname
                try:
                    return open( single_dataset.file_name )
                except:
                    return 'This dataset contains no content'
        else:
            return 'Wrong format';
