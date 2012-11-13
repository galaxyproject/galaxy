import sys, os, ConfigParser, logging, shutil
from time import strftime
from datetime import date

log = logging.getLogger( __name__ )

class HgWebConfigManager( object ):
    def __init__( self ):
        self.hgweb_config_dir = None
        self.in_memory_config = None
    def add_entry( self, lhs, rhs ):
        """Add an entry in the hgweb.config file for a new repository."""
        # Since we're changing the config, make sure the latest is loaded into memory.
        self.read_config( force_read=True )
        # An entry looks something like: repos/test/mira_assembler = database/community_files/000/repo_123.
        if rhs.startswith( './' ):
            rhs = rhs.replace( './', '', 1 )
        self.make_backup()
        # Add the new entry into memory.
        self.in_memory_config.set( 'paths', lhs, rhs )
        # Persist our in-memory configuration.
        self.write_config()
    def change_entry( self, old_lhs, new_lhs, new_rhs ):
        """Change an entry in the hgweb.config file for a repository - this only happens when the owner changes the name of the repository."""
        self.make_backup()
        # Remove the old entry.
        self.in_memory_config.remove_option( 'paths', old_lhs )
        # Add the new entry.
        self.in_memory_config.set( 'paths', new_lhs, new_rhs )
        # Persist our in-memory configuration.
        self.write_config()
    def get_entry( self, lhs ):
        """Return an entry in the hgweb.config file for a repository"""
        self.read_config()
        try:
            entry = self.in_memory_config.get( 'paths', lhs )
        except ConfigParser.NoOptionError:
            raise Exception( "Entry for repository %s missing in file %s." % ( lhs, self.hgweb_config ) )
        return entry
    @property
    def hgweb_config( self ):
        hgweb_config = os.path.join( self.hgweb_config_dir, 'hgweb.config' )
        if not os.path.exists( hgweb_config ):
            raise Exception( "Required file %s does not exist - check config setting for hgweb_config_dir." % hgweb_config )
        return os.path.abspath( hgweb_config )
    def make_backup( self ):
        # Make a backup of the hgweb.config file.
        today = date.today()
        backup_date = today.strftime( "%Y_%m_%d" )
        hgweb_config_backup_filename = 'hgweb.config_%s_backup' % backup_date
        hgweb_config_copy = os.path.join( self.hgweb_config_dir, hgweb_config_backup_filename )
        shutil.copy( os.path.abspath( self.hgweb_config ), os.path.abspath( hgweb_config_copy ) )
    def read_config( self, force_read=False ):
        if force_read or self.in_memory_config is None:
            config = ConfigParser.ConfigParser()
            config.read( self.hgweb_config )
            self.in_memory_config = config
    def write_config( self ):
        """Writing the in-memory configuration to the hgweb.config file on disk."""
        config_file = open( self.hgweb_config, 'wb' )
        self.in_memory_config.write( config_file )
        config_file.close
    