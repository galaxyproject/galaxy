"""
API operations on the datasets from library.
"""
import glob
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
from galaxy import web
from galaxy import util
from galaxy import exceptions
from galaxy.exceptions import ObjectNotFound
from paste.httpexceptions import HTTPBadRequest, HTTPInternalServerError
from galaxy.web import _future_expose_api as expose_api
from galaxy.web import _future_expose_api_anonymous as expose_api_anonymous
from galaxy.security import Action
from galaxy.util.streamball import StreamBall
from galaxy.web.base.controller import BaseAPIController, UsesVisualizationMixin

import logging
log = logging.getLogger( __name__ )


class LibraryDatasetsController( BaseAPIController, UsesVisualizationMixin ):

    @expose_api_anonymous
    def show( self, trans, id, **kwd ):
        """
        show( self, trans, id, **kwd )
        * GET /api/libraries/datasets/{encoded_dataset_id}:
            Displays information about the dataset identified by the encoded ID.

        :param  id:      the encoded id of the dataset to query
        :type   id:      an encoded id string

        :rtype:     dictionary
        :returns:   detailed dataset information from base controller
        .. seealso:: :attr:`galaxy.web.base.controller.UsesLibraryMixinItems.get_library_dataset`
        """
        try:
            dataset = self.get_library_dataset( trans, id=id, check_ownership=False, check_accessible=True )
        except Exception:
            raise exceptions.ObjectNotFound( 'Requested dataset was not found.' )
        rval = trans.security.encode_all_ids( dataset.to_dict() )
        rval[ 'deleted' ] = dataset.deleted
        rval[ 'folder_id' ] = 'F' + rval[ 'folder_id' ]
        return rval

    @expose_api
    def delete( self, trans, encoded_dataset_id, **kwd ):
        """
        delete( self, trans, encoded_dataset_id, **kwd ):
        * DELETE /api/libraries/datasets/{encoded_dataset_id}
            Marks the dataset deleted or undeletes it based on the value
            of the undelete flag (if present).
        """
        undelete = util.string_as_bool( kwd.get( 'undelete', False ) )
        try:
            dataset = self.get_library_dataset( trans, id=encoded_dataset_id, check_ownership=False, check_accessible=False )
        except Exception, e:
            raise exceptions.ObjectNotFound( 'Requested dataset was not found.' + str(e) )
        current_user_roles = trans.get_current_user_roles()
        allowed = trans.app.security_agent.can_modify_library_item( current_user_roles, dataset )
        if ( not allowed ) and ( not trans.user_is_admin() ):
            raise exceptions.InsufficientPermissionsException( 'You do not have proper permissions to delete this dataset.')

        if undelete:
            dataset.deleted = False
        else:
            dataset.deleted = True

        trans.sa_session.add( dataset )
        trans.sa_session.flush()

        rval = trans.security.encode_all_ids( dataset.to_dict() )
        rval[ 'update_time' ] = dataset.update_time.strftime( "%Y-%m-%d %I:%M %p" )
        rval[ 'deleted' ] = dataset.deleted
        rval[ 'folder_id' ] = 'F' + rval[ 'folder_id' ]
        return rval

    @web.expose
    def download( self, trans, format, **kwd ):
        """
        download( self, trans, format, **kwd )
        * GET /api/libraries/datasets/download/{format}
        * POST /api/libraries/datasets/download/{format}
            Downloads requested datasets (identified by encoded IDs) in requested format.

        example: ``GET localhost:8080/api/libraries/datasets/download/tbz?ldda_ids%255B%255D=a0d84b45643a2678&ldda_ids%255B%255D=fe38c84dcd46c828``

        .. note:: supported format values are: 'zip', 'tgz', 'tbz', 'uncompressed'

        :param  format:      string representing requested archive format
        :type   format:      string
        :param  lddas[]:      an array of encoded ids
        :type   lddas[]:      an array

        :rtype:   file
        :returns: either archive with the requested datasets packed inside or a single uncompressed dataset

        :raises: MessageException, ItemDeletionException, ItemAccessibilityException, HTTPBadRequest, OSError, IOError, ObjectNotFound
        """
        lddas = []
        datasets_to_download = kwd[ 'ldda_ids%5B%5D' ]

        if ( datasets_to_download is not None ):
            datasets_to_download = util.listify( datasets_to_download )
            for dataset_id in datasets_to_download:
                try:
                    ldda = self.get_hda_or_ldda( trans, hda_ldda='ldda', dataset_id=dataset_id )
                    lddas.append( ldda )
                except HTTPBadRequest, e:
                    raise exceptions.RequestParameterInvalidException( 'Bad Request. ' + str( e.err_msg ) )
                except HTTPInternalServerError, e:
                    raise exceptions.InternalServerError( 'Internal error. ' + str( e.err_msg ) )
                except Exception, e:
                    raise exceptions.InternalServerError( 'Unknown error. ' + str( e ) )

        if format in [ 'zip', 'tgz', 'tbz' ]:
                # error = False
                killme = string.punctuation + string.whitespace
                trantab = string.maketrans( killme, '_'*len( killme ) )
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
                        archive.add = lambda x, y: archive.write( x, y.encode( 'CP437' ) )
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
                    log.exception( "Unable to create archive for download" )
                    raise exceptions.InternalServerError( "Unable to create archive for download." )
                except Exception:
                    log.exception( "Unexpected error %s in create archive for download" % sys.exc_info()[ 0 ] )
                    raise exceptions.InternalServerError( "Unable to create archive for download." )
                composite_extensions = trans.app.datatypes_registry.get_composite_extensions()
                seen = []
                for ldda in lddas:
                    ext = ldda.extension
                    is_composite = ext in composite_extensions
                    path = ""
                    parent_folder = ldda.library_dataset.folder
                    while parent_folder is not None:
                        # Exclude the now-hidden "root folder"
                        if parent_folder.parent is None:
                            path = os.path.join( parent_folder.library_root[ 0 ].name, path )
                            break
                        path = os.path.join( parent_folder.name, path )
                        parent_folder = parent_folder.parent
                    path += ldda.name
                    while path in seen:
                        path += '_'
                    seen.append( path )
                    zpath = os.path.split(path)[ -1 ]  # comes as base_name/fname
                    outfname, zpathext = os.path.splitext( zpath )

                    if is_composite:  # need to add all the components from the extra_files_path to the zip
                        if zpathext == '':
                            zpath = '%s.html' % zpath  # fake the real nature of the html file
                        try:
                            if format == 'zip':
                                archive.add( ldda.dataset.file_name, zpath )  # add the primary of a composite set
                            else:
                                archive.add( ldda.dataset.file_name, zpath, check_file=True )  # add the primary of a composite set
                        except IOError:
                            log.exception( "Unable to add composite parent %s to temporary library download archive" % ldda.dataset.file_name )
                            raise exceptions.InternalServerError( "Unable to create archive for download." )
                        except ObjectNotFound:
                            log.exception( "Requested dataset %s does not exist on the host." % ldda.dataset.file_name )
                            raise exceptions.ObjectNotFound( "Requested dataset not found. " )
                        except Exception, e:
                            log.exception( "Unable to add composite parent %s to temporary library download archive" % ldda.dataset.file_name )
                            raise exceptions.InternalServerError( "Unable to add composite parent to temporary library download archive. " + str( e ) )

                        flist = glob.glob(os.path.join(ldda.dataset.extra_files_path, '*.*'))  # glob returns full paths
                        for fpath in flist:
                            efp, fname = os.path.split(fpath)
                            if fname > '':
                                fname = fname.translate(trantab)
                            try:
                                if format == 'zip':
                                    archive.add( fpath, fname )
                                else:
                                    archive.add( fpath, fname, check_file=True )
                            except IOError:
                                log.exception( "Unable to add %s to temporary library download archive %s" % ( fname, outfname) )
                                raise exceptions.InternalServerError( "Unable to create archive for download." )
                            except ObjectNotFound:
                                log.exception( "Requested dataset %s does not exist on the host." % fpath )
                                raise exceptions.ObjectNotFound( "Requested dataset not found." )
                            except Exception, e:
                                log.exception( "Unable to add %s to temporary library download archive %s" % ( fname, outfname ) )
                                raise exceptions.InternalServerError( "Unable to add dataset to temporary library download archive . " + str( e ) )

                    else:  # simple case
                        try:
                            if format == 'zip':
                                archive.add( ldda.dataset.file_name, path )
                            else:
                                archive.add( ldda.dataset.file_name, path, check_file=True )
                        except IOError:
                            log.exception( "Unable to write %s to temporary library download archive" % ldda.dataset.file_name )
                            raise exceptions.InternalServerError( "Unable to create archive for download" )
                        except ObjectNotFound:
                            log.exception( "Requested dataset %s does not exist on the host." % ldda.dataset.file_name )
                            raise exceptions.ObjectNotFound( "Requested dataset not found." )
                        except Exception, e:
                            log.exception( "Unable to add %s to temporary library download archive %s" % ( fname, outfname ) )
                            raise exceptions.InternalServerError( "Unknown error. " + str( e ) )
                lname = 'selected_dataset'
                fname = lname.replace( ' ', '_' ) + '_files'
                if format == 'zip':
                    archive.close()
                    trans.response.set_content_type( "application/octet-stream" )
                    trans.response.headers[ "Content-Disposition" ] = 'attachment; filename="%s.%s"' % ( fname, outext )
                    archive = util.streamball.ZipBall( tmpf, tmpd )
                    archive.wsgi_status = trans.response.wsgi_status()
                    archive.wsgi_headeritems = trans.response.wsgi_headeritems()
                    return archive.stream
                else:
                    trans.response.set_content_type( "application/x-tar" )
                    trans.response.headers[ "Content-Disposition" ] = 'attachment; filename="%s.%s"' % ( fname, outext )
                    archive.wsgi_status = trans.response.wsgi_status()
                    archive.wsgi_headeritems = trans.response.wsgi_headeritems()
                    return archive.stream
        elif format == 'uncompressed':
            if len(lddas) != 1:
                raise exceptions.RequestParameterInvalidException( "You can download only one uncompressed file at once." )
            else:
                single_dataset = lddas[ 0 ]
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
                    raise exceptions.InternalServerError( "This dataset contains no content." )
        else:
            raise exceptions.RequestParameterInvalidException( "Wrong format parameter specified" )
