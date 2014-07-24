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
            library_dataset = self.get_library_dataset( trans, id=id, check_ownership=False, check_accessible=True )
        except Exception:
            raise exceptions.ObjectNotFound( 'Requested library_dataset was not found.' )

        current_user_roles = trans.get_current_user_roles()

        # Build the full path for breadcrumb purposes.
        full_path = self._build_path( trans, library_dataset.folder )
        dataset_item = ( trans.security.encode_id( library_dataset.id ), library_dataset.name )
        full_path.insert(0, dataset_item)
        full_path = full_path[ ::-1 ]

        nice_size = util.nice_size( int( library_dataset.library_dataset_dataset_association.get_size() ) )

        date_uploaded = library_dataset.library_dataset_dataset_association.create_time.strftime( "%Y-%m-%d %I:%M %p" )

        rval = trans.security.encode_all_ids( library_dataset.to_dict() )
        rval[ 'deleted' ] = library_dataset.deleted
        rval[ 'folder_id' ] = 'F' + rval[ 'folder_id' ]
        rval[ 'full_path' ] = full_path
        rval[ 'file_size' ] = nice_size
        rval[ 'date_uploaded' ] = date_uploaded
        rval[ 'can_user_modify' ] = trans.app.security_agent.can_modify_library_item( current_user_roles, library_dataset) or trans.user_is_admin()
        rval[ 'is_unrestricted' ] = trans.app.security_agent.dataset_is_public( library_dataset.library_dataset_dataset_association.dataset )

        #  Manage dataset permission is always attached to the dataset itself, not the the ld or ldda to maintain consistency
        rval[ 'can_user_manage' ] = trans.app.security_agent.can_manage_dataset( current_user_roles, library_dataset.library_dataset_dataset_association.dataset) or trans.user_is_admin()
        return rval

    @expose_api
    def show_roles( self, trans, encoded_dataset_id, **kwd ):
        """
        show_roles( self, trans, id, **kwd ):
        * GET /api/libraries/datasets/{encoded_dataset_id}/permissions
            Displays information about current or available roles
            for a given dataset permission.

        :param  encoded_dataset_id:      the encoded id of the dataset to query
        :type   encoded_dataset_id:      an encoded id string

        :param  scope:      either 'current' or 'available'
        :type   scope:      string

        :rtype:     dictionary
        :returns:   either dict of current roles for all permission types or
                           dict of available roles to choose from (is the same for any permission type)

        """

        current_user_roles = trans.get_current_user_roles()
        try:
            library_dataset = self.get_library_dataset( trans, id=encoded_dataset_id, check_ownership=False, check_accessible=False )
        except Exception, e:
            raise exceptions.ObjectNotFound( 'Requested dataset was not found.' + str(e) )
        dataset = library_dataset.library_dataset_dataset_association.dataset

        # User has to have manage permissions in order to see the roles.
        can_manage = trans.app.security_agent.can_manage_dataset( current_user_roles, dataset ) or trans.user_is_admin()
        if not can_manage:
            raise exceptions.InsufficientPermissionsException( 'You do not have proper permissions to access permissions.' )

        scope = kwd.get( 'scope', None )

        if scope == 'current' or scope is None:
            return self.get_current_roles( trans, library_dataset )
            # legit_roles = trans.app.security_agent.get_legitimate_roles( trans, dataset, 'library_admin' )
            # log.debug( 'CXXXXXCXCXCXCXCXCC legit roles: ' + str( [ legit_role.name for legit_role in legit_roles ] ) )

            # all_permissions = trans.app.security_agent.get_permissions( library_dataset )
            # for k,v in all_permissions.items():
                # log.debug( '*******************************************' )
                # log.debug( 'permission action: ' + str( k.action ) )
                # log.debug( 'permission roles: ' + str( [ role.name for role in v ] ) )

        #  Return roles that are available to select.
        if scope == 'available':
            page = kwd.get( 'page', None )
            if page is not None:
                page = int( page )
            else:
                page = 1

            page_limit = kwd.get( 'page_limit', None )
            if page_limit is not None:
                page_limit = int( page_limit )
            else:
                page_limit = 10

            query = kwd.get( 'q', None )

            # try:
            #     library_dataset = self.get_library_dataset( trans, id=encoded_dataset_id, check_ownership=False, check_accessible=False )
            # except Exception, e:
            #     raise exceptions.ObjectNotFound( 'Requested dataset was not found.' + str(e) )
            # dataset = library_dataset.library_dataset_dataset_association.dataset
            # library = library_dataset.folder.parent_library

            roles, total_roles = trans.app.security_agent.get_valid_dataset_roles( trans, dataset, query, page, page_limit )

            return_roles = []
            for role in roles:
                return_roles.append( dict( id=role.name, name=role.name, type=role.type ) )

            return dict( roles=return_roles, page=page, page_limit=page_limit, total=total_roles )

    def get_current_roles( self, trans, library_dataset):
        """
        Find all roles currently connected to relevant permissions 
        on the library dataset and the underlying dataset.

        :param  library_dataset:      the model object
        :type   library_dataset:      LibraryDataset
        """
        dataset = library_dataset.library_dataset_dataset_association.dataset

        # Omit duplicated roles by converting to set 
        access_roles = set( dataset.get_access_roles( trans ) )
        modify_roles = set( trans.app.security_agent.get_roles_for_action( library_dataset, trans.app.security_agent.permitted_actions.LIBRARY_MODIFY ) )
        manage_roles = set( dataset.get_manage_permissions_roles( trans ) )

        access_dataset_role_list = [ access_role.name for access_role in access_roles ]
        manage_dataset_role_list = [ manage_role.name for manage_role in manage_roles ]
        modify_item_role_list = [ modify_role.name for modify_role in modify_roles ]

        return dict( access_dataset_roles=access_dataset_role_list, modify_item_roles=modify_item_role_list, manage_dataset_roles=manage_dataset_role_list )

    @expose_api
    def update_permissions( self, trans, encoded_dataset_id, **kwd ):
        """
        def update( self, trans, encoded_dataset_id, **kwd ):
            *POST /api/libraries/datasets/{encoded_dataset_id}/permissions

        :param  encoded_dataset_id:      the encoded id of the dataset to make private
        :type   encoded_dataset_id:      an encoded id string      

        :param  action:     (required) describes what action should be performed
                            available actions: make_private, remove_restrictions, set_permissions
        :type   action:     string        

        :rtype:     dictionary
        :returns:   dict of current roles for all permission types
        """
        try:
            library_dataset = self.get_library_dataset( trans, id=encoded_dataset_id, check_ownership=False, check_accessible=False )
        except Exception, e:
            raise exceptions.ObjectNotFound( 'Requested dataset was not found.' + str(e) )

        dataset = library_dataset.library_dataset_dataset_association.dataset

        current_user_roles = trans.get_current_user_roles()
        can_manage = trans.app.security_agent.can_manage_dataset( current_user_roles, dataset ) or trans.user_is_admin()
        if not can_manage:
            raise exceptions.InsufficientPermissionsException( 'You do not have proper permissions to manage permissions on this dataset.' )

        new_access_roles_ids = kwd.get( 'access_ids[]', None )
        new_manage_roles_ids = kwd.get( 'manage_ids[]', None )
        new_modify_roles_ids = kwd.get( 'modify_ids[]', None )
        # if new_access_roles_ids is None:
        #     new_access_roles_ids = kwd.get( 'access_ids', None )
        # if new_manage_roles_ids is None:
        #     new_manage_roles_ids = kwd.get( 'manage_ids', None )
        # if new_modify_roles_ids is None:
        #     new_modify_roles_ids = kwd.get( 'modify_ids', None )

        action = kwd.get( 'action', None )
        if action is None:
            raise exceptions.RequestParameterMissingException( 'The mandatory parameter "action" is missing.' )
        elif action == 'remove_restrictions':
            trans.app.security_agent.make_dataset_public( dataset )
            if not trans.app.security_agent.dataset_is_public( dataset ):
                raise exceptions.InternalServerError( 'An error occured while making dataset public.' )
        elif action == 'make_private':
            trans.app.security_agent.make_dataset_public( dataset )
            private_role = trans.app.security_agent.get_private_user_role( trans.user )
            dp = trans.app.model.DatasetPermissions( trans.app.security_agent.permitted_actions.DATASET_ACCESS.action, dataset, private_role )
            trans.sa_session.add( dp )
            trans.sa_session.flush()
            if not trans.app.security_agent.dataset_is_private_to_user( trans, library_dataset ):
                raise exceptions.InternalServerError( 'An error occured while making dataset private.' )
        elif action == 'set_permissions':
            # permission = { Action : [ Role, Role ] }
            # trans.app.security_agent.set_dataset_permission( dataset, permission )


            
            raise exceptions.NotImplemented()
        else:
            raise exceptions.RequestParameterInvalidException( 'The mandatory parameter "action" has an invalid value.' 
                                'Allowed values are: "remove_restrictions", "make_private", "set_dataset_access_roles"' )

        return self.get_current_roles( trans, library_dataset )

    @expose_api
    def delete( self, trans, encoded_dataset_id, **kwd ):
        """
        delete( self, trans, encoded_dataset_id, **kwd ):
        * DELETE /api/libraries/datasets/{encoded_dataset_id}
            Marks the dataset deleted or undeleted based on the value
            of the undelete flag. 
            If the flag is not present it is considered False and the
            item is marked deleted.

        :param  encoded_dataset_id:      the encoded id of the dataset to change
        :type   encoded_dataset_id:      an encoded id string    

        :rtype:     dictionary
        :returns:   dict containing information about the dataset
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
        datasets_to_download = kwd.get( 'ldda_ids%5B%5D', None )
        if datasets_to_download is None:
            datasets_to_download = kwd.get( 'ldda_ids', None )

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
        else:
            raise exceptions.RequestParameterMissingException( 'Request has to contain a list of dataset ids to download.' )

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

    def _build_path( self, trans, folder ):
        """
        Search the path upwards recursively and load the whole route of
        names and ids for breadcrumb building purposes.

        :param folder: current folder for navigating up
        :param type:   Galaxy LibraryFolder

        :returns:   list consisting of full path to the library
        :type:      list
        """
        path_to_root = []
        # We are almost in root
        if folder.parent_id is None:
            path_to_root.append( ( 'F' + trans.security.encode_id( folder.id ), folder.name ) )
        else:
        # We add the current folder and traverse up one folder.
            path_to_root.append( ( 'F' + trans.security.encode_id( folder.id ), folder.name ) )
            upper_folder = trans.sa_session.query( trans.app.model.LibraryFolder ).get( folder.parent_id )
            path_to_root.extend( self._build_path( trans, upper_folder ) )
        return path_to_root
