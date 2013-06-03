from galaxy.web.base.controller import BaseUIController
from galaxy import web, util
from galaxy.web.base.controllers.admin import Admin
from galaxy.util import inflector
import tool_shed.util.shed_util_common as suc
import tool_shed.util.metadata_util as metadata_util
import tool_shed.grids.admin_grids as admin_grids

from galaxy import eggs
eggs.require( 'mercurial' )
from mercurial import hg

import logging

log = logging.getLogger( __name__ )


class AdminController( BaseUIController, Admin ):
    
    user_list_grid = admin_grids.UserGrid()
    role_list_grid = admin_grids.RoleGrid()
    group_list_grid = admin_grids.GroupGrid()
    manage_category_grid = admin_grids.ManageCategoryGrid()
    repository_grid = admin_grids.AdminRepositoryGrid()
    repository_metadata_grid = admin_grids.RepositoryMetadataGrid()

    @web.expose
    @web.require_admin
    def browse_repositories( self, trans, **kwd ):
        # We add params to the keyword dict in this method in order to rename the param
        # with an "f-" prefix, simulating filtering by clicking a search link.  We have
        # to take this approach because the "-" character is illegal in HTTP requests.
        if 'operation' in kwd:
            operation = kwd['operation'].lower()
            if operation == "view_or_manage_repository":
                return trans.response.send_redirect( web.url_for( controller='repository',
                                                                  action='browse_repositories',
                                                                  **kwd ) )
            elif operation == "edit_repository":
                return trans.response.send_redirect( web.url_for( controller='repository',
                                                                  action='edit_repository',
                                                                  **kwd ) )
            elif operation == "repositories_by_user":
                # Eliminate the current filters if any exist.
                for k, v in kwd.items():
                    if k.startswith( 'f-' ):
                        del kwd[ k ]
                if 'user_id' in kwd:
                    user = suc.get_user( trans, kwd[ 'user_id' ] )
                    kwd[ 'f-email' ] = user.email
                    del kwd[ 'user_id' ]
                else:
                    # The received id is the repository id, so we need to get the id of the user
                    # that uploaded the repository.
                    repository_id = kwd.get( 'id', None )
                    repository = suc.get_repository_in_tool_shed( trans, repository_id )
                    kwd[ 'f-email' ] = repository.user.email
            elif operation == "repositories_by_category":
                # Eliminate the current filters if any exist.
                for k, v in kwd.items():
                    if k.startswith( 'f-' ):
                        del kwd[ k ]
                category_id = kwd.get( 'id', None )
                category = suc.get_category( trans, category_id )
                kwd[ 'f-Category.name' ] = category.name
            elif operation == "receive email alerts":
                if kwd[ 'id' ]:
                    kwd[ 'caller' ] = 'browse_repositories'
                    return trans.response.send_redirect( web.url_for( controller='repository',
                                                                      action='set_email_alerts',
                                                                      **kwd ) )
                else:
                    del kwd[ 'operation' ]
            elif operation == 'delete':
                return self.delete_repository( trans, **kwd )
            elif operation == "undelete":
                return self.undelete_repository( trans, **kwd )
        # The changeset_revision_select_field in the RepositoryGrid performs a refresh_on_change
        # which sends in request parameters like changeset_revison_1, changeset_revision_2, etc.  One
        # of the many select fields on the grid performed the refresh_on_change, so we loop through 
        # all of the received values to see which value is not the repository tip.  If we find it, we
        # know the refresh_on_change occurred, and we have the necessary repository id and change set
        # revision to pass on.
        for k, v in kwd.items():
            changeset_revision_str = 'changeset_revision_'
            if k.startswith( changeset_revision_str ):
                repository_id = trans.security.encode_id( int( k.lstrip( changeset_revision_str ) ) )
                repository = suc.get_repository_in_tool_shed( trans, repository_id )
                if repository.tip( trans.app ) != v:
                    return trans.response.send_redirect( web.url_for( controller='repository',
                                                                      action='browse_repositories',
                                                                      operation='view_or_manage_repository',
                                                                      id=trans.security.encode_id( repository.id ),
                                                                      changeset_revision=v ) )
        # Render the list view
        return self.repository_grid( trans, **kwd )

    @web.expose
    @web.require_admin
    def browse_repository_metadata( self, trans, **kwd ):
        if 'operation' in kwd:
            operation = kwd[ 'operation' ].lower()
            if operation == "delete":
                return self.delete_repository_metadata( trans, **kwd )
            if operation == "view_or_manage_repository_revision":
                # The received id is a RepositoryMetadata object id, so we need to get the
                # associated Repository and redirect to view_or_manage_repository with the
                # changeset_revision.
                repository_metadata = metadata_util.get_repository_metadata_by_id( trans, kwd[ 'id' ] )
                repository = repository_metadata.repository
                kwd[ 'id' ] = trans.security.encode_id( repository.id )
                kwd[ 'changeset_revision' ] = repository_metadata.changeset_revision
                kwd[ 'operation' ] = 'view_or_manage_repository'
                return trans.response.send_redirect( web.url_for( controller='repository',
                                                                  action='browse_repositories',
                                                                  **kwd ) )
        return self.repository_metadata_grid( trans, **kwd )

    @web.expose
    @web.require_admin
    def create_category( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        name = util.restore_text( params.get( 'name', '' ) ).strip()
        description = util.restore_text( params.get( 'description', '' ) ).strip()
        if params.get( 'create_category_button', False ):
            if not name or not description:
                message = 'Enter a valid name and a description'
                status = 'error'
            elif suc.get_category_by_name( trans, name ):
                message = 'A category with that name already exists'
                status = 'error'
            else:
                # Create the category
                category = trans.app.model.Category( name=name, description=description )
                trans.sa_session.add( category )
                trans.sa_session.flush()
                message = "Category '%s' has been created" % category.name
                status = 'done'
                trans.response.send_redirect( web.url_for( controller='admin',
                                                           action='manage_categories',
                                                           message=message,
                                                           status=status ) )
        return trans.fill_template( '/webapps/tool_shed/category/create_category.mako',
                                    name=name,
                                    description=description,
                                    message=message,
                                    status=status )

    @web.expose
    @web.require_admin
    def delete_repository( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        id = kwd.get( 'id', None )
        if id:
            # Deleting multiple items is currently not allowed (allow_multiple=False), so there will only be 1 id. 
            ids = util.listify( id )
            count = 0
            deleted_repositories = ""
            for repository_id in ids:
                repository = suc.get_repository_in_tool_shed( trans, repository_id )
                if repository:
                    if not repository.deleted:
                        # Mark all installable repository_metadata records as not installable.
                        for repository_metadata in repository.downloadable_revisions:
                            repository_metadata.downloadable = False
                            trans.sa_session.add( repository_metadata )
                        repository.deleted = True
                        trans.sa_session.add( repository )
                        trans.sa_session.flush()
                        count += 1
                        deleted_repositories += " %s " % repository.name
            if count:
                message = "Deleted %d %s: %s" % ( count, inflector.cond_plural( len( ids ), "repository" ), deleted_repositories )
            else:
                message = "All selected repositories were already marked deleted."
        else:
            message = "No repository ids received for deleting."
            status = 'error'
        trans.response.send_redirect( web.url_for( controller='admin',
                                                   action='browse_repositories',
                                                   message=util.sanitize_text( message ),
                                                   status=status ) )

    @web.expose
    @web.require_admin
    def delete_repository_metadata( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        id = kwd.get( 'id', None )
        if id:
            ids = util.listify( id )
            count = 0
            for repository_metadata_id in ids:
                repository_metadata = metadata_util.get_repository_metadata_by_id( trans, repository_metadata_id )
                trans.sa_session.delete( repository_metadata )
                trans.sa_session.flush()
                count += 1
            if count:
                message = "Deleted %d repository metadata %s" % ( count, inflector.cond_plural( len( ids ), "record" ) )
        else:
            message = "No repository metadata ids received for deleting."
            status = 'error'
        trans.response.send_redirect( web.url_for( controller='admin',
                                                   action='browse_repository_metadata',
                                                   message=util.sanitize_text( message ),
                                                   status=status ) )

    @web.expose
    @web.require_admin
    def edit_category( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        id = params.get( 'id', None )
        if not id:
            message = "No category ids received for editing"
            trans.response.send_redirect( web.url_for( controller='admin',
                                                       action='manage_categories',
                                                       message=message,
                                                       status='error' ) )
        category = suc.get_category( trans, id )
        if params.get( 'edit_category_button', False ):
            new_name = util.restore_text( params.get( 'name', '' ) ).strip()
            new_description = util.restore_text( params.get( 'description', '' ) ).strip()
            if category.name != new_name or category.description != new_description:
                if not new_name:
                    message = 'Enter a valid name'
                    status = 'error'
                elif category.name != new_name and suc.get_category_by_name( trans, name ):
                    message = 'A category with that name already exists'
                    status = 'error'
                else:
                    category.name = new_name
                    category.description = new_description
                    trans.sa_session.add( category )
                    trans.sa_session.flush()
                    message = "The information has been saved for category '%s'" % ( category.name )
                    status = 'done'
                    return trans.response.send_redirect( web.url_for( controller='admin',
                                                                      action='manage_categories',
                                                                      message=message,
                                                                      status=status ) )
        return trans.fill_template( '/webapps/tool_shed/category/edit_category.mako',
                                    category=category,
                                    message=message,
                                    status=status )

    @web.expose
    @web.require_admin
    def manage_categories( self, trans, **kwd ):
        if 'f-free-text-search' in kwd:
            # Trick to enable searching repository name, description from the CategoryGrid.
            # What we've done is rendered the search box for the RepositoryGrid on the grid.mako
            # template for the CategoryGrid.  See ~/templates/webapps/tool_shed/category/grid.mako.
            # Since we are searching repositories and not categories, redirect to browse_repositories().
            return trans.response.send_redirect( web.url_for( controller='admin',
                                                              action='browse_repositories',
                                                              **kwd ) )
        if 'operation' in kwd:
            operation = kwd['operation'].lower()
            if operation == "create":
                return trans.response.send_redirect( web.url_for( controller='admin',
                                                                  action='create_category',
                                                                  **kwd ) )
            elif operation == "delete":
                return trans.response.send_redirect( web.url_for( controller='admin',
                                                                  action='mark_category_deleted',
                                                                  **kwd ) )
            elif operation == "undelete":
                return trans.response.send_redirect( web.url_for( controller='admin',
                                                                  action='undelete_category',
                                                                  **kwd ) )
            elif operation == "purge":
                return trans.response.send_redirect( web.url_for( controller='admin',
                                                                  action='purge_category',
                                                                  **kwd ) )
            elif operation == "edit":
                return trans.response.send_redirect( web.url_for( controller='admin',
                                                                  action='edit_category',
                                                                  **kwd ) )
        return self.manage_category_grid( trans, **kwd )

    @web.expose
    @web.require_admin
    def regenerate_statistics( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        if 'regenerate_statistics_button' in kwd:
            trans.app.shed_counter.generate_statistics()
            message = "Successfully regenerated statistics"
        return trans.fill_template( '/webapps/tool_shed/admin/statistics.mako',
                                    message=message,
                                    status=status )

    @web.expose
    @web.require_admin
    def reset_metadata_on_selected_repositories_in_tool_shed( self, trans, **kwd ):
        if 'reset_metadata_on_selected_repositories_button' in kwd:
            message, status = metadata_util.reset_metadata_on_selected_repositories( trans, **kwd )
        else:
            message = util.restore_text( kwd.get( 'message', ''  ) )
            status = kwd.get( 'status', 'done' )
        repositories_select_field = suc.build_repository_ids_select_field( trans )
        return trans.fill_template( '/webapps/tool_shed/common/reset_metadata_on_selected_repositories.mako',
                                    repositories_select_field=repositories_select_field,
                                    message=message,
                                    status=status )

    @web.expose
    @web.require_admin
    def undelete_repository( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        id = kwd.get( 'id', None )
        if id:
            # Undeleting multiple items is currently not allowed (allow_multiple=False), so there will only be 1 id.
            ids = util.listify( id )
            count = 0
            undeleted_repositories = ""
            for repository_id in ids:
                repository = suc.get_repository_in_tool_shed( trans, repository_id )
                if repository:
                    if repository.deleted:
                        # Inspect all repository_metadata records to determine those that are installable, and mark them accordingly.
                        for repository_metadata in repository.metadata_revisions:
                            metadata = repository_metadata.metadata
                            if metadata:
                                if metadata_util.is_downloadable( metadata ):
                                    repository_metadata.downloadable = True
                                    trans.sa_session.add( repository_metadata )
                        repository.deleted = False
                        trans.sa_session.add( repository )
                        trans.sa_session.flush()
                        count += 1
                        undeleted_repositories += " %s" % repository.name
            if count:
                message = "Undeleted %d %s: %s" % ( count, inflector.cond_plural( count, "repository" ), undeleted_repositories )
            else:
                message = "No selected repositories were marked deleted, so they could not be undeleted."
        else:
            message = "No repository ids received for undeleting."
            status = 'error'
        trans.response.send_redirect( web.url_for( controller='admin',
                                                   action='browse_repositories',
                                                   message=util.sanitize_text( message ),
                                                   status='done' ) )

    @web.expose
    @web.require_admin
    def mark_category_deleted( self, trans, **kwd ):
        # TODO: We should probably eliminate the Category.deleted column since it really makes no
        # sense to mark a category as deleted (category names and descriptions can be changed instead).
        # If we do this, and the following 2 methods can be eliminated.
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        id = kwd.get( 'id', None )
        if id:
            ids = util.listify( id )
            message = "Deleted %d categories: " % len( ids )
            for category_id in ids:
                category = suc.get_category( trans, category_id )
                category.deleted = True
                trans.sa_session.add( category )
                trans.sa_session.flush()
                message += " %s " % category.name
        else:
            message = "No category ids received for deleting."
            status = 'error'
        trans.response.send_redirect( web.url_for( controller='admin',
                                                   action='manage_categories',
                                                   message=util.sanitize_text( message ),
                                                   status='done' ) )

    @web.expose
    @web.require_admin
    def purge_category( self, trans, **kwd ):
        # This method should only be called for a Category that has previously been deleted.
        # Purging a deleted Category deletes all of the following from the database:
        # - RepoitoryCategoryAssociations where category_id == Category.id
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        id = kwd.get( 'id', None )
        if id:
            ids = util.listify( id )
            count = 0
            purged_categories = ""
            message = "Purged %d categories: " % len( ids )
            for category_id in ids:
                category = suc.get_category( trans, category_id )
                if category.deleted:
                    # Delete RepositoryCategoryAssociations
                    for rca in category.repositories:
                        trans.sa_session.delete( rca )
                    trans.sa_session.flush()
                    purged_categories += " %s " % category.name
            message = "Purged %d categories: %s" % ( count, purged_categories )
        else:
            message = "No category ids received for purging."
            status = 'error'
        trans.response.send_redirect( web.url_for( controller='admin',
                                                   action='manage_categories',
                                                   message=util.sanitize_text( message ),
                                                   status='done' ) )

    @web.expose
    @web.require_admin
    def undelete_category( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        id = kwd.get( 'id', None )
        if id:
            ids = util.listify( id )
            count = 0
            undeleted_categories = ""
            for category_id in ids:
                category = suc.get_category( trans, category_id )
                if category.deleted:
                    category.deleted = False
                    trans.sa_session.add( category )
                    trans.sa_session.flush()
                    count += 1
                    undeleted_categories += " %s" % category.name
            message = "Undeleted %d categories: %s" % ( count, undeleted_categories )
        else:
            message = "No category ids received for undeleting."
            status = 'error'
        trans.response.send_redirect( web.url_for( controller='admin',
                                                   action='manage_categories',
                                                   message=util.sanitize_text( message ),
                                                   status='done' ) )
