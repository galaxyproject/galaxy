""" Build indexes for searching the TS """
import sys
import os
import ConfigParser

new_path = [ os.path.join( os.getcwd(), "lib" ) ]
new_path.extend( sys.path[1:] )  # remove scripts/ from the path
sys.path = new_path

from galaxy.util import pretty_print_time_interval
import galaxy.webapps.tool_shed.model.mapping
from galaxy.webapps.tool_shed import config, model

from galaxy import eggs
eggs.require( "SQLAlchemy" )
eggs.require( "Whoosh" )
from whoosh.filedb.filestore import FileStorage
from whoosh.fields import Schema, STORED, TEXT

repo_schema = Schema(
    id=STORED,
    name=TEXT( stored=True ),
    description=TEXT( stored=True ),
    long_description=TEXT( stored=True ),
    homepage_url=TEXT( stored=True ),
    remote_repository_url=TEXT( stored=True ),
    repo_owner_username=TEXT( stored=True ),
    times_downloaded=STORED,
    approved=STORED,
    last_updated=STORED,
    full_last_updated=STORED )

tool_schema = Schema(
    name=TEXT( stored=True ),
    description=TEXT( stored=True ),
    owner=TEXT( stored=True ),
    id=TEXT( stored=True ),
    help=TEXT( stored=True ),
    version=TEXT( stored=True),
    repo_owner_username=TEXT( stored=True ),
    repo_id=STORED )


def build_index( sa_session, toolshed_whoosh_index_dir ):
    """
    Build the search indexes. One for repositories and another for tools within.
    """
    repo_index_storage = FileStorage( toolshed_whoosh_index_dir )
    tool_index_dir = os.path.join( toolshed_whoosh_index_dir, 'tools' )
    #  Rare race condition exists here
    if not os.path.exists( tool_index_dir ):
        os.makedirs( tool_index_dir )
    tool_index_storage = FileStorage( tool_index_dir )

    repo_index = repo_index_storage.create_index( repo_schema )
    tool_index = tool_index_storage.create_index( tool_schema )

    repo_index_writer = repo_index.writer()
    tool_index_writer = tool_index.writer()

    def to_unicode( a_basestr ):
        if type( a_basestr ) is str:
            return unicode( a_basestr, 'utf-8' )
        else:
            return a_basestr

    repos_indexed = 0
    tools_indexed = 0

    for repo in get_repos( sa_session ):

        repo_index_writer.add_document( id=repo.get( 'id' ),
                             name=to_unicode( repo.get( 'name' ) ),
                             description=to_unicode( repo.get( 'description' ) ),
                             long_description=to_unicode( repo.get( 'long_description' ) ),
                             homepage_url=to_unicode( repo.get( 'homepage_url' ) ),
                             remote_repository_url=to_unicode( repo.get( 'remote_repository_url' ) ),
                             repo_owner_username=to_unicode( repo.get( 'repo_owner_username' ) ),
                             times_downloaded=repo.get( 'times_downloaded' ),
                             approved=repo.get( 'approved' ),
                             last_updated=repo.get( 'last_updated' ),
                             full_last_updated=repo.get( 'full_last_updated' ) )
        #  Tools get their own index
        for tool in repo.get( 'tools_dict' ):
            # print tool
            tool_index_writer.add_document( id=to_unicode( tool.get( 'id' ) ),
                                            name=to_unicode( tool.get( 'name' ) ),
                                            version=to_unicode( tool.get( 'version' ) ),
                                            description=to_unicode( tool.get( 'description' ) ),
                                            help=to_unicode( tool.get( 'help' ) ),
                                            repo_owner_username=to_unicode( repo.get( 'repo_owner_username' ) ),
                                            repo_id=repo.get( 'id' ) )
            tools_indexed += 1

        repos_indexed += 1

    tool_index_writer.commit()
    repo_index_writer.commit()

    print "Number of repos indexed: ", repos_indexed
    print "Number of tools indexed: ", tools_indexed


def get_repos( sa_session ):
    """
    Load repos from DB
    """
    results = []
    for repo in sa_session.query( model.Repository ).filter_by( deleted=False ).filter_by( deprecated=False ).filter( model.Repository.type != 'tool_dependency_definition' ):

        repo_id = repo.id
        name = repo.name
        description = repo.description
        long_description = repo.long_description
        homepage_url = repo.homepage_url
        remote_repository_url = repo.remote_repository_url

        times_downloaded = repo.times_downloaded
        if not isinstance( times_downloaded, ( int, long ) ):
            times_downloaded = 0

        repo_owner_username = ''
        if repo.user_id is not None:
            user = sa_session.query( model.User ).filter( model.User.id == repo.user_id ).one()
            repo_owner_username = user.username

        approved = 'no'
        for review in repo.reviews:
            if review.approved == 'yes':
                approved = 'yes'
                break

        #  Format the time since last update to be nicely readable.
        last_updated = pretty_print_time_interval( repo.update_time )
        full_last_updated = repo.update_time.strftime( "%Y-%m-%d %I:%M %p" )

        #  Parse all the tools within repo for separate index.
        tools_dict = []
        from galaxy.webapps.tool_shed.model import directory_hash_id
        path = os.path.join( '/Users/marten/devel/git/galaxy/database/community_files', *directory_hash_id( repo.id ))
        path = os.path.join( path, "repo_%d" % repo.id )
        from galaxy.tools.loader_directory import load_tool_elements_from_path
        if os.path.exists(path):
            tool_elems = load_tool_elements_from_path(path)
            if tool_elems:
                for elem in tool_elems:
                    root = elem[1].getroot()
                    if root.tag == 'tool':
                        tools_dict.append( dict( id=root.attrib.get('id'),
                                                 name=root.attrib.get('name'),
                                                 version=root.attrib.get('version'),
                                                 description=root.find('description').text,
                                                 help=root.find('help').text ) )

        results.append(dict( id=repo_id,
                             name=name,
                             description=description,
                             long_description=long_description,
                             homepage_url=homepage_url,
                             remote_repository_url=remote_repository_url,
                             repo_owner_username=repo_owner_username,
                             times_downloaded=times_downloaded,
                             approved=approved,
                             last_updated=last_updated,
                             full_last_updated=full_last_updated,
                             tools_dict=tools_dict ) )
    return results


def get_sa_session_and_needed_config_settings( ini_file ):
    conf_parser = ConfigParser.ConfigParser( { 'here' : os.getcwd() } )
    conf_parser.read( ini_file )
    kwds = dict()
    for key, value in conf_parser.items( "app:main" ):
        kwds[ key ] = value
    config_settings = config.Configuration( **kwds )
    db_con = config_settings.database_connection
    if not db_con:
        db_con = "sqlite:///%s?isolation_level=IMMEDIATE" % config_settings.database
    model = galaxy.webapps.tool_shed.model.mapping.init( config_settings.file_path, db_con, engine_options={}, create_tables=False )
    return model.context.current, config_settings

if __name__ == "__main__":
    ini_file = sys.argv[ 1 ]
    sa_session, config_settings = get_sa_session_and_needed_config_settings( ini_file )
    toolshed_whoosh_index_dir = config_settings.get( 'toolshed_whoosh_index_dir', None )
    build_index( sa_session, toolshed_whoosh_index_dir )
