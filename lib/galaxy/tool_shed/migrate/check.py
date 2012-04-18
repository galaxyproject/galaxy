import sys, os, logging, subprocess
from galaxy import eggs
import pkg_resources
pkg_resources.require( "sqlalchemy-migrate" )

from migrate.versioning import repository, schema
from sqlalchemy import *
from common import *

log = logging.getLogger( __name__ )

# Path relative to galaxy
migrate_repository_directory = os.path.dirname( __file__ ).replace( os.getcwd() + os.path.sep, '', 1 )
migrate_repository = repository.Repository( migrate_repository_directory )
dialect_to_egg = { 
    "sqlite" : "pysqlite>=2",
    "postgres" : "psycopg2",
    "mysql" : "MySQL_python"
}

def verify_tools( app, url, galaxy_config_file, engine_options={} ):
    # Check the value in the migrate_tools.version database table column to verify that the number is in
    # sync with the number of version scripts in ~/lib/galaxy/tools/migrate/versions.
    dialect = ( url.split( ':', 1 ) )[0]
    try:
        egg = dialect_to_egg[ dialect ]
        try:
            pkg_resources.require( egg )
            log.debug( "%s egg successfully loaded for %s dialect" % ( egg, dialect ) )
        except:
            # If the module is in the path elsewhere (i.e. non-egg), it'll still load.
            log.warning( "%s egg not found, but an attempt will be made to use %s anyway" % ( egg, dialect ) )
    except KeyError:
        # Let this go, it could possibly work with db's we don't support
        log.error( "database_connection contains an unknown SQLAlchemy database dialect: %s" % dialect )
    # Create engine and metadata
    engine = create_engine( url, **engine_options )
    meta = MetaData( bind=engine )
    # The migrate_tools table was created in database version script 0092_add_migrate_tools_table.py.
    version_table = Table( "migrate_tools", meta, autoload=True )
    # Verify that the code and the database are in sync.
    db_schema = schema.ControlledSchema( engine, migrate_repository )
    latest_tool_migration_script_number = migrate_repository.versions.latest
    if latest_tool_migration_script_number != db_schema.version:
        if app.new_installation:
            # New installations will not be missing tools, so we don't need to worry about them.
            missing_tool_configs = []
        else:
            tool_panel_configs = get_non_shed_tool_panel_configs( app )
            if tool_panel_configs:
                missing_tool_configs = check_for_missing_tools( tool_panel_configs, latest_tool_migration_script_number )
            else:
                missing_tool_configs = []
        config_arg = ''
        if os.path.abspath( os.path.join( os.getcwd(), 'universe_wsgi.ini' ) ) != galaxy_config_file:
            config_arg = ' -c %s' % galaxy_config_file.replace( os.path.abspath( os.getcwd() ), '.' )
        if not app.config.running_functional_tests:
            # Automatically update the value of the migrate_tools.version database table column.
            cmd = 'sh manage_tools.sh%s upgrade'  % config_arg
            proc = subprocess.Popen( args=cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT )
            return_code = proc.wait()
            output = proc.stdout.read( 32768 )
            if return_code != 0:
                raise Exception( "Error attempting to update the value of migrate_tools.version: %s" % output )
            elif missing_tool_configs:
                if len( tool_panel_configs ) == 1:
                    plural = ''
                    tool_panel_config_file_names = tool_panel_configs[ 0 ]
                else:
                    plural = 's'
                    tool_panel_config_file_names = ', '.join( tool_panel_configs )
                msg = "\n>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
                msg += "\n\nThe list of files at the end of this message refers to tools that are configured to load into the tool panel for\n"
                msg += "this Galaxy instance, but have been removed from the Galaxy distribution.  These tools can be automatically installed\n"
                msg += "from the Galaxy tool shed at http://toolshed.g2.bx.psu.edu.\n\n"
                msg += "To skip this process, attempt to start your Galaxy server again (e.g., sh run.sh or whatever you use).  If you do this,\n"
                msg += "be aware that these tools will no longer be available in your Galaxy tool panel, and entries for each of them should\n"
                msg += "be removed from your file%s named %s.\n\n" % ( plural, tool_panel_config_file_names )
                msg += "CRITICAL NOTE IF YOU PLAN TO INSTALL\n"
                msg += "The location in which the tool repositories will be installed is the value of the 'tool_path' attribute in the <tool>\n"
                msg += 'tag of the file named ./migrated_tool_conf.xml (i.e., <toolbox tool_path="../shed_tools">).  The default location\n'
                msg += "setting is '../shed_tools', which may be problematic for some cluster environments, so make sure to change it before\n"
                msg += "you execute the installation process if appropriate.  The configured location must be outside of the Galaxy installation\n"
                msg += "directory or it must be in a sub-directory protected by a properly configured .hgignore file if the directory is within\n"
                msg += "the Galaxy installation directory hierarchy.  This is because tool shed repositories will be installed using mercurial's\n"
                msg += "clone feature, which creates .hg directories and associated mercurial repository files.  Not having .hgignore properly\n"
                msg += "configured could result in undesired behavior when modifying or updating your local Galaxy instance or the tool shed\n"
                msg += "repositories if they are in directories that pose conflicts.  See mercurial's .hgignore documentation at the following\n"
                msg += "URL for details.\n\nhttp://mercurial.selenic.com/wiki/.hgignore\n\n"
                msg += output
                msg += "After the installation process finishes, you can start your Galaxy server.  As part of this installation process,\n"
                msg += "entries for each of the following tool config files will be added to the file named ./migrated_tool_conf.xml, so these\n"
                msg += "tools will continue to be loaded into your tool panel.  Because of this, existing entries for these files should be\n"
                msg += "removed from your file%s named %s, but only after the installation process finishes.\n\n" % ( plural, tool_panel_config_file_names )
                for i, missing_tool_config in enumerate( missing_tool_configs ):
                    msg += "%s\n" % missing_tool_config
                    # Should we do the following?
                    #if i > 10:
                    #    msg += "\n...and %d more tools...\n" % ( len( missing_tool_configs ) - ( i + 1 ) )
                    #    break
                msg += "<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<\n"
                raise Exception( msg )
    else:
        log.info( "At migrate_tools version %d" % db_schema.version )

def migrate_to_current_version( engine, schema ):
    # Changes to get to current version.
    changeset = schema.changeset( None )
    for ver, change in changeset:
        nextver = ver + changeset.step
        log.info( 'Installing tools from version %s -> %s... ' % ( ver, nextver ) )
        old_stdout = sys.stdout
        class FakeStdout( object ):
            def __init__( self ):
                self.buffer = []
            def write( self, s ):
                self.buffer.append( s )
            def flush( self ):
                pass
        sys.stdout = FakeStdout()
        try:
            schema.runchange( ver, change, changeset.step )
        finally:
            for message in "".join( sys.stdout.buffer ).split( "\n" ):
                log.info( message )
            sys.stdout = old_stdout
