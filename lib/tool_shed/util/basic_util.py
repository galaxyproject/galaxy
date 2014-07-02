import logging
import os
import shutil
import sys
from string import Template

from galaxy.util import unicodify

from galaxy import eggs

eggs.require( 'MarkupSafe' )
import markupsafe

log = logging.getLogger( __name__ )

CHUNK_SIZE = 2**20 # 1Mb
INSTALLATION_LOG = 'INSTALLATION.log'
# Set no activity timeout to 20 minutes.
NO_OUTPUT_TIMEOUT = 1200.0
MAXDIFFSIZE = 8000
MAX_DISPLAY_SIZE = 32768

DOCKER_IMAGE_TEMPLATE = '''
# Galaxy Docker image

FROM bgruening/galaxy-stable

MAINTAINER Bjoern A. Gruning, bjoern.gruening@gmail.com

RUN sed -i 's|brand.*|brand = deepTools|g' ~/galaxy-central/universe_wsgi.ini

WORKDIR /galaxy-central

${selected_repositories}

# Mark one folder as imported from the host.
VOLUME ["/export/"]

# Expose port 80 to the host
EXPOSE :80

# Autostart script that is invoked during container start
CMD ["/usr/bin/startup"]
'''

SELECTED_REPOSITORIES_TEMPLATE = '''
RUN service postgresql start && service apache2 start && ./run.sh --daemon && sleep 120 && python ./scripts/api/install_tool_shed_repositories.py --api admin -l http://localhost:8080 --url ${tool_shed_url} -o ${repository_owner} --name ${repository_name} --tool-deps --repository-deps --panel-section-name 'Docker'
'''

def evaluate_template( text, install_environment ):
    """
    Substitute variables defined in XML blocks from dependencies file.  The value of the received
    repository_install_dir is the root installation directory of the repository that contains the
    tool dependency.  The value of the received install_dir is the root installation directory of
    the tool_dependency.
    """
    return Template( text ).safe_substitute( get_env_var_values( install_environment ) )

def get_env_var_values( install_environment ):
    """
    Return a dictionary of values, some of which enable substitution of reserved words for the values.
    The received install_enviroment object has 2 important attributes for reserved word substitution:
    install_environment.tool_shed_repository_install_dir is the root installation directory of the repository
    that contains the tool dependency being installed, and install_environment.install_dir is the root
    installation directory of the tool dependency.
    """
    env_var_dict = {}
    env_var_dict[ 'REPOSITORY_INSTALL_DIR' ] = install_environment.tool_shed_repository_install_dir
    env_var_dict[ 'INSTALL_DIR' ] = install_environment.install_dir
    env_var_dict[ 'system_install' ] = install_environment.install_dir
    # If the Python interpreter is 64bit then we can safely assume that the underlying system is also 64bit.
    env_var_dict[ '__is64bit__' ] = sys.maxsize > 2**32
    return env_var_dict

def get_file_type_str( changeset_revision, file_type ):
    if file_type == 'zip':
        file_type_str = '%s.zip' % changeset_revision
    elif file_type == 'bz2':
        file_type_str = '%s.tar.bz2' % changeset_revision
    elif file_type == 'gz':
        file_type_str = '%s.tar.gz' % changeset_revision
    else:
        file_type_str = ''
    return file_type_str

def move_file( current_dir, source, destination, rename_to=None ):
    source_path = os.path.abspath( os.path.join( current_dir, source ) )
    source_file = os.path.basename( source_path )
    if rename_to is not None:
        destination_file = rename_to
        destination_directory = os.path.join( destination )
        destination_path = os.path.join( destination_directory, destination_file )
    else:
        destination_directory = os.path.join( destination )
        destination_path = os.path.join( destination_directory, source_file )
    if not os.path.exists( destination_directory ):
        os.makedirs( destination_directory )
    shutil.move( source_path, destination_path )

def remove_dir( dir ):
    """Attempt to remove a directory from disk."""
    if dir:
        if os.path.exists( dir ):
            try:
                shutil.rmtree( dir )
            except:
                pass

def size_string( raw_text, size=MAX_DISPLAY_SIZE ):
    """Return a subset of a string (up to MAX_DISPLAY_SIZE) translated to a safe string for display in a browser."""
    if raw_text and len( raw_text ) >= size:
        large_str = '\nFile contents truncated because file size is larger than maximum viewing size of %s\n' % util.nice_size( size )
        raw_text = '%s%s' % ( raw_text[ 0:size ], large_str )
    return raw_text or ''

def stringify( list ):
    if list:
        return ','.join( list )
    return ''

def strip_path( fpath ):
    """Attempt to strip the path from a file name."""
    if not fpath:
        return fpath
    try:
        file_path, file_name = os.path.split( fpath )
    except:
        file_name = fpath
    return file_name

def to_html_string( text ):
    """Translates the characters in text to an html string"""
    if text:
        try:
            text = unicodify( text )
        except UnicodeDecodeError, e:
            return "Error decoding string: %s" % str( e )
        text = unicode( markupsafe.escape( text ) )
        text = text.replace( '\n', '<br/>' )
        text = text.replace( '    ', '&nbsp;&nbsp;&nbsp;&nbsp;' )
        text = text.replace( ' ', '&nbsp;' )
    return text
