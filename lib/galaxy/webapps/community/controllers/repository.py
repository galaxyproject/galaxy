import os, logging, urllib, ConfigParser, tempfile, shutil, pexpect
from time import strftime
from datetime import *

from galaxy import util
from galaxy.datatypes.checkers import *
from galaxy.web.base.controller import *
from galaxy.web.form_builder import CheckboxField
from galaxy.webapps.community import model
from galaxy.webapps.community.model import directory_hash_id
from galaxy.web.framework.helpers import time_ago, iff, grids
from galaxy.util.json import from_json_string, to_json_string
from galaxy.model.orm import *
from common import *
from mercurial import hg, ui, patch

log = logging.getLogger( __name__ )

# Characters that must be html escaped
MAPPED_CHARS = { '>' :'&gt;', 
                 '<' :'&lt;',
                 '"' : '&quot;',
                 '&' : '&amp;',
                 '\'' : '&apos;' }
MAX_CONTENT_SIZE = 32768
VALID_CHARS = set( string.letters + string.digits + "'\"-=_.()/+*^,:?!#[]%\\$@;{}" )
VALID_REPOSITORYNAME_RE = re.compile( "^[a-z0-9\_]+$" )
    
class CategoryListGrid( grids.Grid ):
    class NameColumn( grids.TextColumn ):
        def get_value( self, trans, grid, category ):
            return category.name
    class DescriptionColumn( grids.TextColumn ):
        def get_value( self, trans, grid, category ):
            return category.description
    class RepositoriesColumn( grids.TextColumn ):
        def get_value( self, trans, grid, category ):
            if category.repositories:
                viewable_repositories = 0
                for rca in category.repositories:
                    viewable_repositories += 1
                return viewable_repositories
            return 0

    # Grid definition
    webapp = "community"
    title = "Categories"
    model_class = model.Category
    template='/webapps/community/category/grid.mako'
    default_sort_key = "name"
    columns = [
        NameColumn( "Name",
                    key="name",
                    link=( lambda item: dict( operation="repositories_by_category", id=item.id, webapp="community" ) ),
                    attach_popup=False,
                    filterable="advanced" ),
        DescriptionColumn( "Description",
                    key="description",
                    attach_popup=False,
                    filterable="advanced" ),
        # Columns that are valid for filtering but are not visible.
        grids.DeletedColumn( "Deleted",
                             key="deleted",
                             visible=False,
                             filterable="advanced" ),
        RepositoriesColumn( "Repositories",
                            model_class=model.Repository,
                            attach_popup=False )
    ]

    # Override these
    global_actions = []
    operations = []
    standard_filters = []
    num_rows_per_page = 50
    preserve_state = False
    use_paging = True

class RepositoryListGrid( grids.Grid ):
    class NameColumn( grids.TextColumn ):
        def get_value( self, trans, grid, repository ):
            return repository.name
    class VersionColumn( grids.TextColumn ):
        def get_value( self, trans, grid, repository ):
            repo = hg.repository( ui.ui(), repository.repo_path )
            return get_repository_tip( repo )
    class DescriptionColumn( grids.TextColumn ):
        def get_value( self, trans, grid, repository ):
            return repository.description
    class CategoryColumn( grids.TextColumn ):
        def get_value( self, trans, grid, repository ):
            rval = '<ul>'
            if repository.categories:
                for rca in repository.categories:
                    rval += '<li><a href="browse_repositories?operation=repositories_by_category&id=%s&webapp=community">%s</a></li>' \
                        % ( trans.security.encode_id( rca.category.id ), rca.category.name )
            else:
                rval += '<li>not set</li>'
            rval += '</ul>'
            return rval
    class RepositoryCategoryColumn( grids.GridColumn ):
        def filter( self, trans, user, query, column_filter ):
            """Modify query to filter by category."""
            if column_filter == "All":
                pass
            return query.filter( model.Category.name == column_filter )
    class UserColumn( grids.TextColumn ):
        def get_value( self, trans, grid, repository ):
            if repository.user:
                return repository.user.username
            return 'no user'
    class EmailColumn( grids.TextColumn ):
        def filter( self, trans, user, query, column_filter ):
            if column_filter == 'All':
                return query
            return query.filter( and_( model.Repository.table.c.user_id == model.User.table.c.id,
                                       model.User.table.c.email == column_filter ) )
    class EmailAlertsColumn( grids.TextColumn ):
        def get_value( self, trans, grid, repository ):
            if trans.user.email in from_json_string( repository.email_alerts ):
                return 'yes'
            return ''
    # Grid definition
    title = "Repositories"
    model_class = model.Repository
    template='/webapps/community/repository/grid.mako'
    default_sort_key = "name"
    columns = [
        NameColumn( "Name",
                    key="Repository.name",
                    link=( lambda item: dict( operation="view_or_manage_repository", id=item.id, webapp="community" ) ),
                    attach_popup=False ),
        DescriptionColumn( "Description",
                           key="description",
                           attach_popup=False ),
        VersionColumn( "Version",
                       attach_popup=False ),
        CategoryColumn( "Category",
                        model_class=model.Category,
                        key="Category.name",
                        attach_popup=False ),
        UserColumn( "Owner",
                     model_class=model.User,
                     link=( lambda item: dict( operation="repositories_by_user", id=item.id, webapp="community" ) ),
                     attach_popup=False,
                     key="username" ),
        grids.CommunityRatingColumn( "Average Rating",
                                     key="rating" ),
        EmailAlertsColumn( "Alert",
                           attach_popup=False ),
        # Columns that are valid for filtering but are not visible.
        EmailColumn( "Email",
                     model_class=model.User,
                     key="email",
                     visible=False ),
        RepositoryCategoryColumn( "Category",
                                  model_class=model.Category,
                                  key="Category.name",
                                  visible=False )
    ]
    columns.append( grids.MulticolFilterColumn( "Search repository name, description", 
                                                cols_to_filter=[ columns[0], columns[1] ],
                                                key="free-text-search",
                                                visible=False,
                                                filterable="standard" ) )
    operations = [ grids.GridOperation( "Receive email alerts",
                                        allow_multiple=True,
                                        condition=( lambda item: not item.deleted ),
                                        async_compatible=False ) ]
    standard_filters = []
    default_filter = {}
    num_rows_per_page = 50
    preserve_state = False
    use_paging = True
    def build_initial_query( self, trans, **kwd ):
        return trans.sa_session.query( self.model_class ) \
                               .join( model.User.table ) \
                               .outerjoin( model.RepositoryCategoryAssociation.table ) \
                               .outerjoin( model.Category.table )

class RepositoryController( BaseController, ItemRatings ):

    repository_list_grid = RepositoryListGrid()
    category_list_grid = CategoryListGrid()

    @web.expose
    def index( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        return trans.fill_template( '/webapps/community/index.mako', message=message, status=status )
    @web.expose
    def browse_categories( self, trans, **kwd ):
        if 'f-free-text-search' in kwd:
            # Trick to enable searching repository name, description from the CategoryListGrid.
            # What we've done is rendered the search box for the RepositoryListGrid on the grid.mako
            # template for the CategoryListGrid.  See ~/templates/webapps/community/category/grid.mako.
            # Since we are searching repositories and not categories, redirect to browse_repositories().
            return self.browse_repositories( trans, **kwd )
        if 'operation' in kwd:
            operation = kwd['operation'].lower()
            if operation in [ "repositories_by_category", "repositories_by_user" ]:
                # Eliminate the current filters if any exist.
                for k, v in kwd.items():
                    if k.startswith( 'f-' ):
                        del kwd[ k ]
                return trans.response.send_redirect( web.url_for( controller='repository',
                                                                  action='browse_repositories',
                                                                  **kwd ) )
        # Render the list view
        return self.category_list_grid( trans, **kwd )
    @web.expose
    def browse_repositories( self, trans, **kwd ):
        # We add params to the keyword dict in this method in order to rename the param
        # with an "f-" prefix, simulating filtering by clicking a search link.  We have
        # to take this approach because the "-" character is illegal in HTTP requests.
        if 'operation' in kwd:
            operation = kwd['operation'].lower()
            if operation == "view_or_manage_repository":
                repository_id = kwd.get( 'id', None )
                repository = get_repository( trans, repository_id )
                if repository.user == trans.user:
                    return trans.response.send_redirect( web.url_for( controller='repository',
                                                                      action='manage_repository',
                                                                      **kwd ) )
                else:
                    return trans.response.send_redirect( web.url_for( controller='repository',
                                                                      action='view_repository',
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
                    user = get_user( trans, kwd[ 'user_id' ] )
                    kwd[ 'f-email' ] = user.email
                    del kwd[ 'user_id' ]
                else:
                    # The received id is the repository id, so we need to get the id of the user
                    # that uploaded the repository.
                    repository_id = kwd.get( 'id', None )
                    repository = get_repository( trans, repository_id )
                    kwd[ 'f-email' ] = repository.user.email
            elif operation == "my_repositories":
                # Eliminate the current filters if any exist.
                for k, v in kwd.items():
                    if k.startswith( 'f-' ):
                        del kwd[ k ]
                kwd[ 'f-email' ] = trans.user.email
            elif operation == "repositories_by_category":
                # Eliminate the current filters if any exist.
                for k, v in kwd.items():
                    if k.startswith( 'f-' ):
                        del kwd[ k ]
                category_id = kwd.get( 'id', None )
                category = get_category( trans, category_id )
                kwd[ 'f-Category.name' ] = category.name
            elif operation == "receive email alerts":
                return trans.response.send_redirect( web.url_for( controller='repository',
                                                                  action='set_email_alerts',
                                                                  **kwd ) )
        # Render the list view
        return self.repository_list_grid( trans, **kwd )
    @web.expose
    def create_repository( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        categories = get_categories( trans )
        if not categories:
            message = 'No categories have been configured in this instance of the Galaxy Tool Shed.  ' + \
                'An administrator needs to create some via the Administrator control panel before creating repositories.',
            status = 'error'
            return trans.response.send_redirect( web.url_for( controller='repository',
                                                              action='browse_repositories',
                                                              message=message,
                                                              status=status ) )
        name = util.restore_text( params.get( 'name', '' ) )
        description = util.restore_text( params.get( 'description', '' ) )
        category_ids = util.listify( params.get( 'category_id', '' ) )
        selected_categories = [ trans.security.decode_id( id ) for id in category_ids ]
        if params.get( 'create_repository_button', False ):
            error = False
            message = self.__validate_repository_name( name, trans.user )
            if message:
                error = True
            if not description:
                message = 'Enter a description.'
                error = True
            if not error:
                # Add the repository record to the db
                repository = trans.app.model.Repository( name=name, description=description, user_id=trans.user.id )
                # Flush to get the id
                trans.sa_session.add( repository )
                trans.sa_session.flush()
                # Determine the repository's repo_path on disk
                dir = os.path.join( trans.app.config.file_path, *directory_hash_id( repository.id ) )
                # Create directory if it does not exist
                if not os.path.exists( dir ):
                    os.makedirs( dir )
                # Define repo name inside hashed directory
                repository_path = os.path.join( dir, "repo_%d" % repository.id )
                # Create local repository directory
                if not os.path.exists( repository_path ):
                    os.makedirs( repository_path )
                # Create the local repository
                repo = hg.repository( ui.ui(), repository_path, create=True )
                # Add an entry in the hgweb.config file for the local repository
                # This enables calls to repository.repo_path
                self.__add_hgweb_config_entry( trans, repository, repository_path )
                # Create a .hg/hgrc file for the local repository
                self.__create_hgrc_file( repository )
                flush_needed = False
                if category_ids:
                    # Create category associations
                    for category_id in category_ids:
                        category = trans.app.model.Category.get( trans.security.decode_id( category_id ) )
                        rca = trans.app.model.RepositoryCategoryAssociation( repository, category )
                        trans.sa_session.add( rca )
                        flush_needed = True
                if flush_needed:
                    trans.sa_session.flush()
                message = "Repository '%s' has been created." % repository.name
                trans.response.send_redirect( web.url_for( controller='repository',
                                                           action='view_repository',
                                                           message=message,
                                                           id=trans.security.encode_id( repository.id ) ) )
        return trans.fill_template( '/webapps/community/repository/create_repository.mako',
                                    name=name,
                                    description=description,
                                    selected_categories=selected_categories,
                                    categories=categories,
                                    message=message,
                                    status=status )
    def __validate_repository_name( self, name, user ):
        # Repository names must be unique for each user, must be at least four characters
        # in length and must contain only lower-case letters, numbers, and the '_' character.
        if name in [ 'None', None, '' ]:
            return 'Enter the required repository name.'
        for repository in user.active_repositories:
            if repository.name == name:
                return "You already have a repository named '%s', so choose a different name." % name
        if len( name ) < 4:
            return "Repository names must be at least 4 characters in length."
        if len( name ) > 80:
            return "Repository names cannot be more than 80 characters in length."
        if not( VALID_REPOSITORYNAME_RE.match( name ) ):
            return "Repository names must contain only lower-case letters, numbers and underscore '_'."
        return ''
    def __add_hgweb_config_entry( self, trans, repository, repository_path ):
        # Add an entry in the hgweb.config file for a new repository.
        # An entry looks something like:
        # repos/test/mira_assembler = database/community_files/000/repo_123.
        hgweb_config = "%s/hgweb.config" %  trans.app.config.root
        entry = "repos/%s/%s = %s" % ( repository.user.username, repository.name, repository_path.lstrip( './' ) )
        if os.path.exists( hgweb_config ):
            output = open( hgweb_config, 'a' )
        else:
            output = open( hgweb_config, 'w' )
            output.write( '[paths]\n' )
        output.write( "%s\n" % entry )
        output.close()
    def __create_hgrc_file( self, repository ):
        # At this point, an entry for the repository is required to be in the hgweb.config
        # file so we can call repository.repo_path.
        # Create a .hg/hgrc file that looks something like this:
        # [web]
        # allow_push = test
        # name = convert_characters1
        # push_ssl = False
        # Upon repository creation, only the owner can push to it ( allow_push setting ),
        # and since we support both http and https, we set push_ssl to False to override
        # the default (which is True) in the mercurial api.
        hgrc_file = os.path.abspath( os.path.join( repository.repo_path, ".hg", "hgrc" ) )
        output = open( hgrc_file, 'w' )
        output.write( '[web]\n' )
        output.write( 'allow_push = %s\n' % repository.user.username )
        output.write( 'name = %s\n' % repository.name )
        output.write( 'push_ssl = false\n' )
        output.flush()
        output.close()
    def __get_allow_push( self, repository ):
        # TODO: Use the mercurial api to handle this
        hgrc_file = os.path.abspath( os.path.join( repository.repo_path, ".hg", "hgrc" ) )
        config = ConfigParser.ConfigParser()
        config.read( hgrc_file )
        for option in config.options( "web" ):
            if option == 'allow_push':
                return config.get( "web", option )
        raise Exception( "Repository %s missing allow_push entry under the [web] option in it's hgrc file." % repository.name )
    def __set_allow_push( self, repository, usernames, remove_auth='' ):
        """
        # TODO: Use the mercurial api to handle this, something like the following:
        items = repo.ui.configitems( section, untrusted=False )
        push_section = repo.ui.config( 'hgrc', 'allow_push' )
        for XXX (in name you want to add):
            repo.ui.updateconfig( section=extensions_section, name='XXX', value='YYY' )
        """
        hgrc_file = os.path.abspath( os.path.join( repository.repo_path, ".hg", "hgrc" ) )
        fh, fn = tempfile.mkstemp()
        for i, line in enumerate( open( hgrc_file ) ):
            if line.startswith( 'allow_push' ):
                value = line.split( ' = ' )[1].rstrip( '\n' )
                if remove_auth:
                    current_usernames = value.split( ',' )
                    new_usernames = []
                    for current_username in current_usernames:
                        if current_username != remove_auth:
                            new_usernames.append( current_username )
                    new_usernames = ','.join( new_usernames )
                    line = 'allow_push = %s\n' % new_usernames
                else:
                    value = '%s,%s\n' % ( value, usernames )
                    line = 'allow_push = %s' % value
            os.write( fh, line )
        os.close( fh )
        shutil.move( fn, hgrc_file )
    @web.expose
    def browse_repository( self, trans, id, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        commit_message = util.restore_text( params.get( 'commit_message', 'Deleted selected files' ) )
        repository = get_repository( trans, id )
        repo = hg.repository( ui.ui(), repository.repo_path )
        # Our current support for browsing a repository requires copies of the
        # repository files to be in the repository root directory.  We do the
        # following to ensure the latest files are being browsed.
        current_working_dir = os.getcwd()
        repo_dir = repository.repo_path
        os.chdir( repo_dir )
        os.system( 'hg update > /dev/null 2>&1' )
        os.chdir( current_working_dir )
        return trans.fill_template( '/webapps/community/repository/browse_repository.mako',
                                    repo=repo,
                                    repository=repository,
                                    commit_message=commit_message,
                                    message=message,
                                    status=status )
    @web.expose
    def select_files_to_delete( self, trans, id, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', '' ) )
        status = params.get( 'status', 'done' )
        commit_message = util.restore_text( params.get( 'commit_message', 'Deleted selected files' ) )
        repository = get_repository( trans, id )
        _ui = ui.ui()
        repo_dir = repository.repo_path
        repo = hg.repository( _ui, repo_dir )
        selected_files_to_delete = util.restore_text( params.get( 'selected_files_to_delete', '' ) )
        if params.get( 'select_files_to_delete_button', False ):
            if selected_files_to_delete:
                selected_files_to_delete = selected_files_to_delete.split( ',' )
                current_working_dir = os.getcwd()
                # Get the current repository tip.
                tip = repo[ 'tip' ]
                # Clone the repository to a temporary location.
                tmp_dir, cloned_repo_dir = hg_clone( trans, repository, current_working_dir )
                # Delete the selected files from the repository.
                cloned_repo = hg.repository( _ui, cloned_repo_dir )
                for selected_file in selected_files_to_delete:
                    selected_file_path = selected_file.split( 'repo_%d' % repository.id )[ 1 ].lstrip( '/' )
                    hg_remove( selected_file_path, current_working_dir, cloned_repo_dir )
                # Commit the change set.
                if not commit_message:
                    commit_message = 'Deleted selected files'
                hg_commit( commit_message, current_working_dir, cloned_repo_dir )
                # Push the change set from the cloned repository to the master repository.
                hg_push( trans, repository, current_working_dir, cloned_repo_dir )
                # Remove the temporary directory containing the cloned repository.
                shutil.rmtree( tmp_dir )
                # Update the repository files for browsing.
                update_for_browsing( repository, current_working_dir )
                # Get the new repository tip.
                repo = hg.repository( _ui, repo_dir )
                if tip != repo[ 'tip' ]:
                    message = "The selected files were deleted from the repository."
                else:
                    message = 'No changes to repository.'
            else:
                message = "Select at least 1 file to delete from the repository before clicking <b>Delete selected files</b>."
                status = "error"
        return trans.fill_template( '/webapps/community/repository/browse_repository.mako',
                                    repo=repo,
                                    repository=repository,
                                    commit_message=commit_message,
                                    message=message,
                                    status=status )
    @web.expose
    def view_repository( self, trans, id, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        repository = get_repository( trans, id )
        repo = hg.repository( ui.ui(), repository.repo_path )
        tip = get_repository_tip( repo )
        avg_rating, num_ratings = self.get_ave_item_rating_data( trans.sa_session, repository, webapp_model=trans.model )
        display_reviews = util.string_as_bool( params.get( 'display_reviews', False ) )
        alerts = params.get( 'alerts', '' )
        alerts_checked = CheckboxField.is_checked( alerts )
        if repository.email_alerts:
            email_alerts = from_json_string( repository.email_alerts )
        else:
            email_alerts = []
        user = trans.user
        if params.get( 'receive_email_alerts_button', False ):
            flush_needed = False
            if alerts_checked:
                if user.email not in email_alerts:
                    email_alerts.append( user.email )
                    repository.email_alerts = to_json_string( email_alerts )
                    flush_needed = True
            else:
                if user.email in email_alerts:
                    email_alerts.remove( user.email )
                    repository.email_alerts = to_json_string( email_alerts )
                    flush_needed = True
            if flush_needed:
                trans.sa_session.add( repository )
                trans.sa_session.flush()
        checked = alerts_checked or user.email in email_alerts
        alerts_check_box = CheckboxField( 'alerts', checked=checked )
        return trans.fill_template( '/webapps/community/repository/view_repository.mako',
                                    repo=repo,
                                    repository=repository,
                                    tip=tip,
                                    avg_rating=avg_rating,
                                    display_reviews=display_reviews,
                                    num_ratings=num_ratings,
                                    alerts_check_box=alerts_check_box,
                                    message=message,
                                    status=status )
    @web.expose
    @web.require_login( "manage repository" )
    def manage_repository( self, trans, id, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        repository = get_repository( trans, id )
        repo = hg.repository( ui.ui(), repository.repo_path )
        tip = get_repository_tip( repo )
        repo_name = util.restore_text( params.get( 'repo_name', repository.name ) )
        description = util.restore_text( params.get( 'description', repository.description ) )
        avg_rating, num_ratings = self.get_ave_item_rating_data( trans.sa_session, repository, webapp_model=trans.model )
        display_reviews = util.string_as_bool( params.get( 'display_reviews', False ) )
        alerts = params.get( 'alerts', '' )
        alerts_checked = CheckboxField.is_checked( alerts )
        if repository.email_alerts:
            email_alerts = from_json_string( repository.email_alerts )
        else:
            email_alerts = []
        allow_push = params.get( 'allow_push', '' )
        error = False
        user = trans.user
        if params.get( 'edit_repository_button', False ):
            flush_needed = False
            if user != repository.user:
                message = "You are not the owner of this repository, so you cannot manage it."
                status = error
                return trans.response.send_redirect( web.url_for( controller='repository',
                                                                  action='view_repository',
                                                                  id=id,
                                                                  message=message,
                                                                  status=status ) )
            if repo_name != repository.name:
                message = self.__validate_repository_name( repo_name, user )
                if message:
                    error = True
                else:
                    repository.name = repo_name
                    flush_needed = True
            if description != repository.description:
                repository.description = description
                flush_needed = True
            if flush_needed:
                trans.sa_session.add( repository )
                trans.sa_session.flush()
        elif params.get( 'user_access_button', False ):
            if allow_push not in [ 'none' ]:
                remove_auth = params.get( 'remove_auth', '' )
                if remove_auth:
                    usernames = ''
                else:
                    user_ids = util.listify( allow_push )
                    usernames = []
                    for user_id in user_ids:
                        user = trans.sa_session.query( trans.model.User ).get( trans.security.decode_id( user_id ) )
                        usernames.append( user.username )
                    usernames = ','.join( usernames )
                self.__set_allow_push( repository, usernames, remove_auth=remove_auth )
        elif params.get( 'receive_email_alerts_button', False ):
            flush_needed = False
            if alerts_checked:
                if user.email not in email_alerts:
                    email_alerts.append( user.email )
                    repository.email_alerts = to_json_string( email_alerts )
                    flush_needed = True
            else:
                if user.email in email_alerts:
                    email_alerts.remove( user.email )
                    repository.email_alerts = to_json_string( email_alerts )
                    flush_needed = True
            if flush_needed:
                trans.sa_session.add( repository )
                trans.sa_session.flush()
        if error:
            status = 'error'
        current_allow_push_list = self.__get_allow_push( repository ).split( ',' )
        allow_push_select_field = self.__build_allow_push_select_field( trans, current_allow_push_list )
        checked = alerts_checked or user.email in email_alerts
        alerts_check_box = CheckboxField( 'alerts', checked=checked )
        return trans.fill_template( '/webapps/community/repository/manage_repository.mako',
                                    repo_name=repo_name,
                                    description=description,
                                    current_allow_push_list=current_allow_push_list,
                                    allow_push_select_field=allow_push_select_field,
                                    repo=repo,
                                    repository=repository,
                                    tip=tip,
                                    avg_rating=avg_rating,
                                    display_reviews=display_reviews,
                                    num_ratings=num_ratings,
                                    alerts_check_box=alerts_check_box,
                                    message=message,
                                    status=status )
    @web.expose
    def view_changelog( self, trans, id, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        repository = get_repository( trans, id )
        repo = hg.repository( ui.ui(), repository.repo_path )
        changesets = []
        for changeset in repo.changelog:
            ctx = repo.changectx( changeset )
            t, tz = ctx.date()
            date = datetime( *time.gmtime( float( t ) - tz )[:6] )
            display_date = date.strftime( "%Y-%m-%d" )
            change_dict = { 'ctx' : ctx,
                            'rev' : str( ctx.rev() ),
                            'date' : date,
                            'display_date' : display_date,
                            'description' : ctx.description(),
                            'files' : ctx.files(),
                            'user' : ctx.user(),
                            'parent' : ctx.parents()[0] }
            # Make sure we'll view latest changeset first.
            changesets.insert( 0, change_dict )
        return trans.fill_template( '/webapps/community/repository/view_changelog.mako', 
                                    repository=repository,
                                    changesets=changesets,
                                    message=message,
                                    status=status )
    @web.expose
    def view_changeset( self, trans, id, ctx_str, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        repository = get_repository( trans, id )
        repo = hg.repository( ui.ui(), repository.repo_path )
        found = False
        for changeset in repo.changelog:
            ctx = repo.changectx( changeset )
            if str( ctx ) == ctx_str:
                found = True
                break
        if not found:
            message = "Repository does not include changeset revision '%s'." % str( ctx_str )
            status = 'error'
            return trans.response.send_redirect( web.url_for( controller='repository',
                                                              action='view_changelog',
                                                              id=id,
                                                              message=message,
                                                              status=status ) )
        ctx_parent = ctx.parents()[0]
        modified, added, removed, deleted, unknown, ignored, clean = repo.status( node1=ctx_parent.node(), node2=ctx.node() )
        anchors = modified + added + removed + deleted + unknown + ignored + clean
        diffs = []
        for diff in patch.diff( repo, node1=ctx_parent.node(), node2=ctx.node() ):
            diffs.append( self.to_html_escaped( diff ) )
        return trans.fill_template( '/webapps/community/repository/view_changeset.mako', 
                                    repository=repository,
                                    ctx=ctx,
                                    anchors=anchors,
                                    modified=modified,
                                    added=added,
                                    removed=removed,
                                    deleted=deleted,
                                    unknown=unknown,
                                    ignored=ignored,
                                    clean=clean,
                                    diffs=diffs,
                                    message=message,
                                    status=status )
    @web.expose
    @web.require_login( "rate repositories" )
    def rate_repository( self, trans, **kwd ):
        """ Rate a repository and return updated rating data. """
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        id = params.get( 'id', None )
        if not id:
            return trans.response.send_redirect( web.url_for( controller='repository',
                                                              action='browse_repositories',
                                                              message='Select a repository to rate',
                                                              status='error' ) )
        repository = get_repository( trans, id )
        if repository.user == trans.user:
            return trans.response.send_redirect( web.url_for( controller='repository',
                                                              action='browse_repositories',
                                                              message="You are not allowed to rate your own repository",
                                                              status='error' ) )
        if params.get( 'rate_button', False ):
            rating = int( params.get( 'rating', '0' ) )
            comment = util.restore_text( params.get( 'comment', '' ) )
            rating = self.rate_item( trans, trans.user, repository, rating, comment )
        avg_rating, num_ratings = self.get_ave_item_rating_data( trans.sa_session, repository, webapp_model=trans.model )
        display_reviews = util.string_as_bool( params.get( 'display_reviews', False ) )
        rra = self.get_user_item_rating( trans.sa_session, trans.user, repository, webapp_model=trans.model )
        return trans.fill_template( '/webapps/community/repository/rate_repository.mako', 
                                    repository=repository,
                                    avg_rating=avg_rating,
                                    display_reviews=display_reviews,
                                    num_ratings=num_ratings,
                                    rra=rra,
                                    message=message,
                                    status=status )
    @web.expose
    def set_email_alerts( self, trans, **kwd ):
        # Set email alerts for selected repositories
        params = util.Params( kwd )
        user = trans.user
        repository_ids = util.listify( kwd.get( 'id', '' ) )
        total_alerts_added = 0
        total_alerts_removed = 0
        for repository_id in repository_ids:
            flush_needed = False
            repository = get_repository( trans, repository_id )
            if repository.email_alerts:
                email_alerts = from_json_string( repository.email_alerts )
            else:
                email_alerts = []
            if user.email in email_alerts:
                email_alerts.remove( user.email )
                repository.email_alerts = to_json_string( email_alerts )
                trans.sa_session.add( repository )
                flush_needed = True
                total_alerts_removed += 1
            else:
                email_alerts.append( user.email )
                repository.email_alerts = to_json_string( email_alerts )
                trans.sa_session.add( repository )
                flush_needed = True
                total_alerts_added += 1
        if flush_needed:
            trans.sa_session.flush()
        message = 'Total alerts added: %d, total alerts removed: %d' % ( total_alerts_added, total_alerts_removed )
        kwd[ 'message' ] = message
        kwd[ 'status' ] = 'done'
        del( kwd[ 'operation' ] )
        return trans.response.send_redirect( web.url_for( controller='repository',
                                                          action='browse_repositories',
                                                          **kwd ) )
    @web.expose
    def download( self, trans, repository_id, file_type, **kwd ):
        # Download an archive of the repository files compressed as zip, gz or bz2.
        params = util.Params( kwd )
        repository = get_repository( trans, repository_id )
        # Allow hgweb to handle the download.  This requires the tool shed
        # server account's .hgrc file to include the following setting:
        # [web]
        # allow_archive = bz2, gz, zip
        if file_type == 'zip':
            file_type_str = 'tip.zip'
        elif file_type == 'bz2':
            file_type_str = 'tip.tar.bz2'
        elif file_type == 'gz':
            file_type_str = 'tip.tar.gz'
        download_url = '/repos/%s/%s/archive/%s' % ( repository.user.username, repository.name, file_type_str )
        return trans.response.send_redirect( download_url )
    @web.json
    def open_folder( self, trans, repository_id, key ):
        # The tool shed includes a repository source file browser, which currently depends upon
        # copies of the hg repository file store in the repo_path for browsing.
        # Avoid caching
        trans.response.headers['Pragma'] = 'no-cache'
        trans.response.headers['Expires'] = '0'
        repository = trans.sa_session.query( trans.model.Repository ).get( trans.security.decode_id( repository_id ) )
        folder_path = key
        files_list = self.__get_files( trans, repository, folder_path )
        folder_contents = []
        for filename in files_list:
            is_folder = False
            if filename and filename[-1] == os.sep:
                is_folder = True
            if filename:
                full_path = os.path.join( folder_path, filename )
                node = { "title": filename,
                         "isFolder": is_folder,
                         "isLazy": is_folder,
                         "tooltip": full_path,
                         "key": full_path }
                folder_contents.append( node )
        return folder_contents
    def __get_files( self, trans, repository, folder_path ):
        ok = True
        def print_ticks( d ):
            pass
        cmd  = "ls -p '%s'" % folder_path
        # Handle the authentication message if keys are not set - the message is
        output = pexpect.run( cmd,
                              events={ pexpect.TIMEOUT : print_ticks }, 
                              timeout=10 )
        if 'No such file or directory' in output:
            status = 'error'
            message = "No folder named (%s) exists." % folder_path
            ok = False
        if ok:
            return output.split()
        return trans.response.send_redirect( web.url_for( controller='repository',
                                                          action='browse_repositories',
                                                          operation="view_or_manage_repository",
                                                          id=trans.security.encode_id( repository.id ),
                                                          status=status,
                                                          message=message ) )
    @web.json
    def get_file_contents( self, trans, file_path ):
        # Avoid caching
        trans.response.headers['Pragma'] = 'no-cache'
        trans.response.headers['Expires'] = '0'
        if is_gzip( file_path ):
            to_html = self.to_html_str( '\ngzip compressed file\n' )
        elif is_bz2( file_path ):
            to_html = self.to_html_str( '\nbz2 compressed file\n' )
        elif check_zip( file_path ):
            to_html = self.to_html_str( '\nzip compressed file\n' )
        elif check_binary( file_path ):
            to_html = self.to_html_str( '\nBinary file\n' )
        else:
            to_html = ''
            for i, line in enumerate( open( file_path ) ):
                to_html = '%s%s' % ( to_html, self.to_html_str( line ) )
                if len( to_html ) > MAX_CONTENT_SIZE:
                    large_str = '\nFile contents truncated because file size is larger than maximum viewing size of %s\n' % util.nice_size( MAX_CONTENT_SIZE )
                    to_html = '%s%s' % ( to_html, self.to_html_str( large_str ) )
                    break
        return to_html
    @web.expose
    def help( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        return trans.fill_template( '/webapps/community/repository/help.mako', message=message, status=status, **kwd )
    def to_html_escaped( self, text ):
        """Translates the characters in text to html values"""
        translated = []
        for c in text:
            if c in [ '\r\n', '\n', ' ', '\t' ] or c in VALID_CHARS:
                translated.append( c )
            elif c in MAPPED_CHARS:
                translated.append( MAPPED_CHARS[ c ] )
            else:
                translated.append( 'X' )
        return ''.join( translated )
    def to_html_str( self, text ):
        """Translates the characters in text to sn html string"""
        translated = []
        for c in text:
            if c in VALID_CHARS:
                translated.append( c )
            elif c in MAPPED_CHARS:
                translated.append( MAPPED_CHARS[ c ] )
            elif c == ' ':
                translated.append( '&nbsp;' )
            elif c == '\t':
                translated.append( '&nbsp;&nbsp;&nbsp;&nbsp;' )
            elif c == '\n':
                translated.append( '<br/>' )
            elif c not in [ '\r' ]:
                translated.append( 'X' )
        return ''.join( translated )
    def __build_allow_push_select_field( self, trans, current_push_list, selected_value='none' ):
        options = []
        for user in trans.sa_session.query( trans.model.User ):
            if user.username not in current_push_list:
                options.append( user )
        return build_select_field( trans,
                                   objs=options,
                                   label_attr='username',
                                   select_field_name='allow_push',
                                   selected_value=selected_value,
                                   refresh_on_change=False,
                                   multiple=True )
