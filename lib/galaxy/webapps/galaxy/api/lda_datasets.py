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
from paste.httpexceptions import HTTPBadRequest
from galaxy import util, web
from galaxy.exceptions import ItemAccessibilityException, MessageException, ItemDeletionException, ObjectNotFound
from galaxy.security import Action
from galaxy.util.streamball import StreamBall
from galaxy.web.base.controller import BaseAPIController, UsesVisualizationMixin

import logging
log = logging.getLogger( __name__ )

class LibraryDatasetsController( BaseAPIController, UsesVisualizationMixin ):

    @web.expose_api
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
            dataset = self.get_library_dataset( trans, id = id, check_ownership=False, check_accessible=True )
        except Exception, e:
            trans.response.status = 500
            return str( e )
        try:
            rval = dataset.to_dict()
        except Exception, e:
            rval = "Error in dataset API at listing contents: " + str( e )
            log.error( rval + ": %s" % str(e), exc_info=True )
            trans.response.status = 500
            return "Error in dataset API at listing contents: " + str( e )

        rval['id'] = trans.security.encode_id(rval['id']);
        rval['ldda_id'] = trans.security.encode_id(rval['ldda_id']);
        rval['folder_id'] = 'f' + trans.security.encode_id(rval['folder_id'])
        return rval

    @web.expose
    def download( self, trans, format, **kwd ):
        """
        download( self, trans, format, **kwd )
        * GET /api/libraries/datasets/download/{format}
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
        datasets_to_download = kwd['ldda_ids%5B%5D']

        if ( datasets_to_download != None ):
            datasets_to_download = util.listify( datasets_to_download )
            for dataset_id in datasets_to_download:
                try:
                    ldda = self.get_hda_or_ldda( trans, hda_ldda='ldda', dataset_id=dataset_id )
                    lddas.append( ldda )
                except ItemAccessibilityException:
                    trans.response.status = 403
                    return 'Insufficient rights to access library dataset with id: (%s)'  % str( dataset_id )
                except MessageException:
                    trans.response.status = 400
                    return 'Wrong library dataset id: (%s)'  % str( dataset_id )
                except ItemDeletionException:
                    trans.response.status = 400
                    return 'The item with library dataset id: (%s) is deleted'  % str( dataset_id )
                except HTTPBadRequest, e:
                    return 'http bad request' + str( e.err_msg )
                except Exception, e:
                    trans.response.status = 500
                    return 'error of unknown kind' + str( e )

        if format in [ 'zip','tgz','tbz' ]:
                # error = False
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
                    log.exception( "Unable to create archive for download" )
                    trans.response.status = 500
                    return "Unable to create archive for download, please report this error"
                except:
                     log.exception( "Unexpected error %s in create archive for download" % sys.exc_info()[0] )
                     trans.response.status = 500
                     return "Unable to create archive for download, please report - %s" % sys.exc_info()[0]
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
                    if is_composite: # need to add all the components from the extra_files_path to the zip
                        if zpathext == '':
                            zpath = '%s.html' % zpath # fake the real nature of the html file
                        try:
                            if format=='zip':
                                archive.add( ldda.dataset.file_name, zpath ) # add the primary of a composite set
                            else:                                    
                                archive.add( ldda.dataset.file_name, zpath, check_file=True ) # add the primary of a composite set
                        except IOError:
                            log.exception( "Unable to add composite parent %s to temporary library download archive" % ldda.dataset.file_name)
                            trans.response.status = 500
                            return "Unable to create archive for download, please report this error"
                        except ObjectNotFound:
                            log.exception( "Requested dataset %s does not exist on the host." % ldda.dataset.file_name )
                            trans.response.status = 500
                            return "Requested dataset does not exist on the host."
                        except:
                            trans.response.status = 500
                            return "Unknown error, please report this error"                                
                        flist = glob.glob(os.path.join(ldda.dataset.extra_files_path,'*.*')) # glob returns full paths
                        for fpath in flist:
                            efp,fname = os.path.split(fpath)
                            if fname > '':
                                fname = fname.translate(trantab)
                            try:
                                if format=='zip':
                                    archive.add( fpath,fname )
                                else:
                                    archive.add( fpath,fname, check_file=True  )
                            except IOError:
                                log.exception( "Unable to add %s to temporary library download archive %s" % (fname,outfname))
                                trans.response.status = 500
                                return "Unable to create archive for download, please report this error"
                            except ObjectNotFound:
                                log.exception( "Requested dataset %s does not exist on the host." % fpath )
                                trans.response.status = 500
                                return "Requested dataset does not exist on the host."                                    
                            except:
                                trans.response.status = 500
                                return "Unknown error, please report this error"
                    else: # simple case
                        try:
                            if format=='zip':
                                archive.add( ldda.dataset.file_name, path )
                            else:
                                archive.add( ldda.dataset.file_name, path, check_file=True  )
                        except IOError:
                            log.exception( "Unable to write %s to temporary library download archive" % ldda.dataset.file_name)
                            trans.response.status = 500
                            return "Unable to create archive for download, please report this error"
                        except ObjectNotFound:
                            log.exception( "Requested dataset %s does not exist on the host." % ldda.dataset.file_name )
                            trans.response.status = 500
                            return "Requested dataset does not exist on the host."
                        except:
                            trans.response.status = 500
                            return "Unknown error, please report this error"
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
                trans.response.status = 400
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
                    trans.response.status = 500
                    return 'This dataset contains no content'
        else:
            trans.response.status = 400
            return 'Wrong format parameter specified';
