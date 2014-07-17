import logging
import os
import stat

log = logging.getLogger( __name__ )


class EnvFileBuilder( object ):

    def __init__( self, install_dir ):
        self.install_dir = install_dir
        self.return_code = 0

    def append_line( self, make_executable=True, **kwd ):
        env_var_dict = dict( **kwd )
        env_entry, env_file = self.create_or_update_env_shell_file( self.install_dir, env_var_dict )
        return_code = self.file_append( env_entry, env_file, make_executable=make_executable )
        self.return_code = self.return_code or return_code
        return self.return_code

    @staticmethod
    def create_or_update_env_shell_file( install_dir, env_var_dict ):
        env_var_action = env_var_dict[ 'action' ]
        env_var_value = env_var_dict[ 'value' ]
        if env_var_action in [ 'prepend_to', 'set_to', 'append_to' ]:
            env_var_name = env_var_dict[ 'name' ]
            if env_var_action == 'prepend_to':
                changed_value = '%s:$%s' % ( env_var_value, env_var_name )
            elif env_var_action == 'set_to':
                changed_value = '%s' % env_var_value
            elif env_var_action == 'append_to':
                changed_value = '$%s:%s' % ( env_var_name, env_var_value )
            line = "%s=%s; export %s" % ( env_var_name, changed_value, env_var_name )
        elif env_var_action == "source":
            line = "if [ -f %s ] ; then . %s ; fi" % ( env_var_value, env_var_value )
        else:
            raise Exception( "Unknown shell file action %s" % env_var_action )
        env_shell_file_path = os.path.join( install_dir, 'env.sh' )
        return line, env_shell_file_path

    def file_append( self, text, file_path, make_executable=True ):
        """
        Append a line to a file unless the line already exists in the file.  This method creates the file if
        it doesn't exist.  If make_executable is True, the permissions on the file are set to executable by
        the owner.
        """
        file_dir = os.path.dirname( file_path )
        if not os.path.exists( file_dir ):
            try:
                os.makedirs( file_dir )
            except Exception, e:
                log.exception( str( e ) )
                return 1
        if os.path.exists( file_path ):
            try:
                new_env_file_contents = []
                env_file_contents = file( file_path, 'r' ).readlines()
                # Clean out blank lines from the env.sh file.
                for line in env_file_contents:
                    line = line.rstrip()
                    if line:
                        new_env_file_contents.append( line )
                env_file_contents = new_env_file_contents
            except Exception, e:
                log.exception( str( e ) )
                return 1
        else:
            env_file_handle = open( file_path, 'w' )
            env_file_handle.close()
            env_file_contents = []
        if make_executable:
            # Explicitly set the file's executable bits.
            try:
                os.chmod( file_path, int( '111', base=8 ) | os.stat( file_path )[ stat.ST_MODE ] )
            except Exception, e:
                log.exception( str( e ) )
                return 1
        # Convert the received text to a list, in order to support adding one or more lines to the file.
        if isinstance( text, basestring ):
            text = [ text ]
        for line in text:
            line = line.rstrip()
            if line and line not in env_file_contents:
                env_file_contents.append( line )
        try:
            file( file_path, 'w' ).write( '\n'.join( env_file_contents ) )
        except Exception, e:
            log.exception( str( e ) )
            return 1
        return 0

    def handle_action_shell_file_paths( self, action_dict ):
        shell_file_paths = action_dict.get( 'action_shell_file_paths', [] )
        for shell_file_path in shell_file_paths:
            self.append_line( action="source", value=shell_file_path )
