"""
Dependency management for tools.
"""

import os.path

import logging
log = logging.getLogger( __name__ )

class DependencyManager( object ):
    """
    A DependencyManager attempts to resolve named and versioned dependencies
    by searching for them under a list of directories. Directories should be
    of the form:

        $BASE/name/version/...

    and should each contain a file 'env.sh' which can be sourced to make the
    dependency available in the current shell environment.
    """
    def __init__( self, base_paths=[] ):
        """
        Create a new dependency manager looking for packages under the paths listed
        in `base_paths`.  The default base path is app.config.tool_dependency_dir.
        """
        self.base_paths = []
        for base_path in base_paths:
            if not os.path.exists( base_path ):
                log.warn( "Path '%s' does not exist, ignoring", base_path )
            if not os.path.isdir( base_path ):
                log.warn( "Path '%s' is not directory, ignoring", base_path )
            self.base_paths.append( os.path.abspath( base_path ) )
    def find_dep( self, name, version=None ):
        """
        Attempt to find a dependency named `name` at version `version`. If
        version is None, return the "default" version as determined using a 
        symbolic link (if found). Returns a triple of:
        env_script, base_path, real_version
        """
        if version is None:
            return self._find_dep_default( name )
        else:
            return self._find_dep_versioned( name, version )
    def _find_dep_versioned( self, name, version ):
        for base_path in self.base_paths:
            path = os.path.join( base_path, name, version )
            script = os.path.join( path, 'env.sh' )
            if os.path.exists( script ):
                return script, path, version
            elif os.path.exists( os.path.join( path, 'bin' ) ):
                return None, path, version
        else:
            return None, None, None
    def _find_dep_default( self, name ):
        version = None
        for base_path in self.base_paths:
            path = os.path.join( base_path, name, 'default' )
            if os.path.islink( path ):
                real_path = os.path.realpath( path )
                real_bin = os.path.join( real_path, 'bin' )
                real_version = os.path.basename( real_path )
                script = os.path.join( real_path, 'env.sh' )
                if os.path.exists( script ):
                    return script, real_path, real_version
                elif os.path.exists( os.path.join( real_path, 'bin' ) ):
                    return None, real_path, real_version
        else:
            return None, None, None
