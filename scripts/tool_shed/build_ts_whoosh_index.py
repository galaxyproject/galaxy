"""
Build indexes for searching the TS.
Run this script from the Tool Shed folder, example:

$ python scripts/tool_shed/build_ts_whoosh_index.py -c config/tool_shed.ini

Make sure you adjusted your config to:
 * turn on searching via toolshed_search_on
 * specify whoosh_index_dir where the indexes will be placed

Also make sure that GALAXY_EGGS_PATH variable is properly set
in case you are using non-default location for Galaxy.
"""
import ConfigParser
import os
import sys
from optparse import OptionParser

from whoosh.fields import Schema, STORED, TEXT
from whoosh.filedb.filestore import FileStorage

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, 'lib')))

import galaxy.webapps.tool_shed.model.mapping
from galaxy.tools.loader_directory import load_tool_elements_from_path
from galaxy.util import directory_hash_id, pretty_print_time_interval
from galaxy.webapps.tool_shed import config, model

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
    repo_name=TEXT( stored=True ),
    repo_owner_username=TEXT( stored=True ),
    repo_id=STORED )


def build_index( sa_session, whoosh_index_dir, path_to_repositories ):
    """
    Build the search indexes. One for repositories and another for tools within.
    """
    #  Rare race condition exists here and below
    if not os.path.exists( whoosh_index_dir ):
        os.makedirs( whoosh_index_dir )
    tool_index_dir = os.path.join( whoosh_index_dir, 'tools' )
    if not os.path.exists( tool_index_dir ):
        os.makedirs( tool_index_dir )

    repo_index_storage = FileStorage( whoosh_index_dir )
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

    for repo in get_repos( sa_session, path_to_repositories ):

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
        for tool in repo.get( 'tools_list' ):
            # print tool
            tool_index_writer.add_document( id=to_unicode( tool.get( 'id' ) ),
                                            name=to_unicode( tool.get( 'name' ) ),
                                            version=to_unicode( tool.get( 'version' ) ),
                                            description=to_unicode( tool.get( 'description' ) ),
                                            help=to_unicode( tool.get( 'help' ) ),
                                            repo_owner_username=to_unicode( repo.get( 'repo_owner_username' ) ),
                                            repo_name=to_unicode( repo.get( 'name' ) ),
                                            repo_id=repo.get( 'id' ) )
            tools_indexed += 1
            print tools_indexed, 'tools (', tool.get( 'id' ), ')'

        repos_indexed += 1
        print repos_indexed, 'repos (', repo.get( 'id' ), ')'

    tool_index_writer.commit()
    repo_index_writer.commit()

    print "TOTAL repos indexed: ", repos_indexed
    print "TOTAL tools indexed: ", tools_indexed


def get_repos( sa_session, path_to_repositories ):
    """
    Load repos from DB and included tools from .xml configs.
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
        tools_list = []
        path = os.path.join( path_to_repositories, *directory_hash_id( repo.id ) )
        path = os.path.join( path, "repo_%d" % repo.id )
        if os.path.exists(path):
            tools_list.extend( load_one_dir( path ) )
            for root, dirs, files in os.walk( path ):
                if '.hg' in dirs:
                    dirs.remove('.hg')
                for dirname in dirs:
                    tools_in_dir = load_one_dir( os.path.join( root, dirname ) )
                    tools_list.extend( tools_in_dir )

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
                             tools_list=tools_list ) )
    return results


def load_one_dir( path ):
    tools_in_dir = []
    tool_elems = load_tool_elements_from_path( path )
    if tool_elems:
        for elem in tool_elems:
            root = elem[1].getroot()
            if root.tag == 'tool':
                tool = {}
                if root.find( 'help' ) is not None:
                    tool.update( dict( help=root.find( 'help' ).text ) )
                if root.find( 'description' ) is not None:
                    tool.update( dict( description=root.find( 'description' ).text ) )
                tool.update( dict( id=root.attrib.get( 'id' ),
                                   name=root.attrib.get( 'name' ),
                                   version=root.attrib.get( 'version' ) ) )
                tools_in_dir.append( tool )
    return tools_in_dir


def get_sa_session_and_needed_config_settings( path_to_tool_shed_config ):
    conf_parser = ConfigParser.ConfigParser( { 'here': os.getcwd() } )
    conf_parser.read( path_to_tool_shed_config )
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
    parser = OptionParser()
    parser.add_option("-c", "--config", dest="path_to_tool_shed_config", default="config/tool_shed.ini", help="specify tool_shed.ini location")
    (options, args) = parser.parse_args()
    path_to_tool_shed_config = options.path_to_tool_shed_config
    sa_session, config_settings = get_sa_session_and_needed_config_settings( path_to_tool_shed_config )
    whoosh_index_dir = config_settings.get( 'whoosh_index_dir', None )
    path_to_repositories = config_settings.get( 'file_path', 'database/community_files' )
    build_index( sa_session, whoosh_index_dir, path_to_repositories )
