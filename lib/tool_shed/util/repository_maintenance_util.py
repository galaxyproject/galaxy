import ConfigParser
import logging
import re
import tool_shed.util.shed_util_common as suc
from galaxy.web.form_builder import build_select_field

from galaxy import eggs
eggs.require('mercurial')

from mercurial import commands
from mercurial import hg
from mercurial import patch
from mercurial import ui

log = logging.getLogger( __name__ )

VALID_REPOSITORYNAME_RE = re.compile( "^[a-z0-9\_]+$" )

def build_allow_push_select_field( trans, current_push_list, selected_value='none' ):
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

def change_repository_name_in_hgrc_file( hgrc_file, new_name ):
    config = ConfigParser.ConfigParser()
    config.read( hgrc_file )
    config.read( hgrc_file )
    config.set( 'web', 'name', new_name )
    new_file = open( hgrc_file, 'wb' )
    config.write( new_file )
    new_file.close()

def create_hgrc_file( trans, repository ):
    # At this point, an entry for the repository is required to be in the hgweb.config file so we can call repository.repo_path( trans.app ).
    # Since we support both http and https, we set push_ssl to False to override the default (which is True) in the mercurial api.  The hg
    # purge extension purges all files and directories not being tracked by mercurial in the current repository.  It'll remove unknown files
    # and empty directories.  This is not currently used because it is not supported in the mercurial API.
    repo = hg.repository( suc.get_configured_ui(), path=repository.repo_path( trans.app ) )
    fp = repo.opener( 'hgrc', 'wb' )
    fp.write( '[paths]\n' )
    fp.write( 'default = .\n' )
    fp.write( 'default-push = .\n' )
    fp.write( '[web]\n' )
    fp.write( 'allow_push = %s\n' % repository.user.username )
    fp.write( 'name = %s\n' % repository.name )
    fp.write( 'push_ssl = false\n' )
    fp.write( '[extensions]\n' )
    fp.write( 'hgext.purge=' )
    fp.close()

def validate_repository_name( name, user ):
    # Repository names must be unique for each user, must be at least four characters
    # in length and must contain only lower-case letters, numbers, and the '_' character.
    if name in [ 'None', None, '' ]:
        return 'Enter the required repository name.'
    if name in [ 'repos' ]:
        return "The term <b>%s</b> is a reserved word in the tool shed, so it cannot be used as a repository name." % name
    for repository in user.active_repositories:
        if repository.name == name:
            return "You already have a repository named <b>%s</b>, so choose a different name." % name
    if len( name ) < 4:
        return "Repository names must be at least 4 characters in length."
    if len( name ) > 80:
        return "Repository names cannot be more than 80 characters in length."
    if not( VALID_REPOSITORYNAME_RE.match( name ) ):
        return "Repository names must contain only lower-case letters, numbers and underscore <b>_</b>."
    return ''
