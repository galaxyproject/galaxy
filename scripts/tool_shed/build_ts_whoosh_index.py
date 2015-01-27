# !/usr/bin/env python
""" Build indeces for searching the TS """
import sys, os, csv, urllib, urllib2, ConfigParser
    
new_path = [ os.path.join( os.getcwd(), "lib" ) ]
new_path.extend( sys.path[1:] ) # remove scripts/ from the path
sys.path = new_path

from galaxy import eggs

# Whoosh is compatible with Python 2.5+ Try to import Whoosh and set flag to indicate whether search is enabled.
try:
    eggs.require( "Whoosh" )
    import pkg_resources
    pkg_resources.require( "SQLAlchemy >= 0.4" )

    import whoosh.index
    import galaxy.webapps.tool_shed.model.mapping
    from whoosh.filedb.filestore import FileStorage
    from whoosh.fields import Schema, STORED, ID, KEYWORD, TEXT, STORED
    from whoosh.scoring import BM25F
    from whoosh.qparser import MultifieldParser
    from whoosh.index import Index
    from galaxy.webapps.tool_shed import config, model
    
    whoosh_ready = True
    schema = Schema(
        id = STORED,
        name = TEXT( field_boost = 1.7 ),
        description = TEXT( field_boost = 1.5 ),
        long_description = TEXT,
        repo_type = TEXT,
        homepage_url = TEXT,
        remote_repository_url = TEXT,
        repo_owner_username = TEXT,
        times_downloaded = STORED )

except ImportError, e:
    print 'import error'
    whoosh_ready = False
    schema = None

def build_index( sa_session, toolshed_whoosh_index_dir ):
    storage = FileStorage( toolshed_whoosh_index_dir )
    index = storage.create_index( schema )
    writer = index.writer()
    def to_unicode( a_basestr ):
        if type( a_basestr ) is str:
            return unicode( a_basestr, 'utf-8' )
        else:
            return a_basestr

    repos_indexed = 0
    for id, name, description, long_description, repo_type, homepage_url, remote_repository_url, repo_owner_username, times_downloaded in get_repos( sa_session ):
        writer.add_document( id = id,
                             name = to_unicode( name ),
                             description = to_unicode( description ), 
                             long_description = to_unicode( long_description ), 
                             repo_type = to_unicode( repo_type ), 
                             homepage_url = to_unicode( homepage_url ), 
                             remote_repository_url = to_unicode( remote_repository_url ), 
                             repo_owner_username = to_unicode( repo_owner_username ),
                             times_downloaded = times_downloaded )
        repos_indexed += 1
    writer.commit()
    print "Number of repos indexed: ", repos_indexed

def get_repos( sa_session ):
    for repo in sa_session.query( model.Repository ).filter_by( deleted=False ).filter_by( deprecated=False ).filter( model.Repository.type != 'tool_dependency_definition' ):
        id = repo.id
        name = repo.name
        description = repo.description
        long_description = repo.long_description
        repo_type = repo.type
        homepage_url = repo.homepage_url
        remote_repository_url = repo.remote_repository_url
        times_downloaded = repo.times_downloaded

        repo_owner_username = ""
        if repo.user_id is not None:
            user = sa_session.query( model.User ).filter( model.User.id == repo.user_id ).one()
            repo_owner_username = user.username

        yield id, name, description, long_description, repo_type, homepage_url, remote_repository_url, repo_owner_username, times_downloaded

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
    if whoosh_ready:
        ini_file = sys.argv[ 1 ]
        sa_session, config_settings = get_sa_session_and_needed_config_settings( ini_file )
        toolshed_whoosh_index_dir = config_settings.get( 'toolshed_whoosh_index_dir', None )
        build_index( sa_session, toolshed_whoosh_index_dir )
