import sys, config
from galaxy.web import security
import galaxy.webapps.demo_sequencer.registry

class UniverseApplication( object ):
    """Encapsulates the state of a Universe application"""
    def __init__( self, **kwargs ):
        print >> sys.stderr, "python path is: " + ", ".join( sys.path )
        # Read config file and check for errors
        self.config = config.Configuration( **kwargs )
        self.config.check()
        config.configure_logging( self.config )
        # Set up sequencer actions registry
        self.sequencer_actions_registry = galaxy.webapps.demo_sequencer.registry.Registry( self.config.root, self.config.sequencer_actions_config )
        # Security helper
        self.security = security.SecurityHelper( id_secret=self.config.id_secret )
    def shutdown( self ):
        pass
