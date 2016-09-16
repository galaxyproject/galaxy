"""
Manager and Serializer for Repositories.
"""

import logging
import os
import hashlib

from operator import itemgetter

from galaxy import exceptions
from galaxy import util
from galaxy.util import jstree
from galaxy.util import checkers
from galaxy.util import unicodify
from galaxy.util import pretty_print_time_interval
from galaxy.model import tool_shed_install
from galaxy.managers import base
from tool_shed.util import basic_util

from sqlalchemy import and_
from sqlalchemy.orm.exc import MultipleResultsFound
from sqlalchemy.orm.exc import NoResultFound

log = logging.getLogger( __name__ )


class RepoManager( base.ModelManager ):
    model_class = tool_shed_install.ToolShedRepository

    def __init__( self, app, *args, **kwargs ):
        super( RepoManager, self ).__init__( app, *args, **kwargs )

    def list( self, trans, view='all' ):
        """
        Retrieve all installed repositories from the database.

        :returns:   all TS repository objects in the database
        :rtype:     list of ToolShedRepository

        :raises: ItemAccessibilityException
        """
        if not trans.user_is_admin():
            raise exceptions.ItemAccessibilityException('Only administrators can see repos.')
        # TODO respect `view` that is requested
        repos = trans.sa_session.query( self.model_class ).all()
        return repos

    def get( self, trans, decoded_repo_id ):
        """
        Retrieve the repo identified by the given id from the database.

        :param  id:      the decoded id of the repo
        :type   id:      an decoded id string

        :returns:   installed repository object
        :rtype:     ToolShedRepository

        :raises: ItemAccessibilityException, InconsistentDatabase,
            RequestParameterInvalidException, InternalServerError
        """
        if not trans.user_is_admin():
            raise exceptions.ItemAccessibilityException('Only administrators can see repos.')
        try:
            repo = trans.sa_session.query( self.model_class ).filter( self.model_class.table.c.id == decoded_repo_id ).one()
        except MultipleResultsFound:
            raise exceptions.InconsistentDatabase('Multiple repositories found with the same id.')
        except NoResultFound:
            raise exceptions.RequestParameterInvalidException('No repository found with the id provided.')
        except Exception as e:
            raise exceptions.InternalServerError('Error loading from the database.', e )
        return repo

    def get_tree( self, trans, repo_id, repo_revision=None ):
        """
        Retrieve the contents of the repository's folder and return
        it in a form of json-serialized jstree object.

        :param  repo_id:        the decoded id of the repo
        :type   repo_id:        a decoded id string
        :param  repo_revision:  revision of the repo to retrieve, defaults to tip
        :type   repo_revision:  str

        :returns:   tree in jstree format
        :rtype:     JSTree object
        """
        repo = self.get( trans, repo_id )
        if not repo_revision:
            # if there is no revision specified grab the latest
            repo_revision = repo.changeset_revision
        repo_path = os.path.abspath( os.path.join( repo.repo_path( trans.app, repo_revision ), repo.name ) )
        try:
            repo_jstree = self.__create_jstree( repo_path )
            response = repo_jstree.jsonData()
        except Exception as exception:
            log.debug( str( exception ) )
            raise exceptions.InternalServerError( 'Could not create tree representation of the given folder: ' + str( repo_path ) )
        return response

    def get_versions( self, trans, repo ):
        """
        Query the DB for all installed versions of
        repositories (using owner and repository name)
        and return them sorted by ctx_rev descending.

        :param  repo:      repository to retrieve versions of
        :type   repo:      ToolShedRepository

        :returns:   desc sorted list with version dictionaries
        :rtype:     list of dicts
        """
        versions = []
        repos = trans.sa_session.query( self.model_class ).filter( and_( self.model_class.table.c.name == repo.name,
                                                                         self.model_class.table.c.owner == repo.owner ) ).all()
        for repo in repos:
            versions.append( {'ctx_rev': repo.ctx_rev, 'changeset_revision': repo.changeset_revision, 'id': repo.id } )
        return sorted( versions, key=itemgetter('ctx_rev'), reverse=True )

    def get_file( self, trans, file_path, decoded_repo_id, repo_revision=None ):
        """
        Retrieve the contents of the requested file in the given repository.
        These are returned escaped and trimmed (if needed). Given path is checked
        against the repository path to make sure it is within.

        :param  file_path:          path relative to the repository root
        :type   file_path:          str
        :param  decoded_repo_id:    the decoded id of the repo
        :type   decoded_repo_id:    a decoded id string
        :param  repo_revision:      revision of the repo to browse, defaults to tip
        :type   repo_revision:      str

        :returns:   HTML escaped string
        :rtype:     str
        """
        MAX_CONTENT_SIZE = 1048576
        safe_str = ''
        repo = self.get( trans, decoded_repo_id )
        abs_file_path = os.path.abspath( os.path.join( repo.repo_path( trans.app, repo_revision ), repo.name, file_path ) )
        if not self.is_path_browsable( trans.app, abs_file_path, repo ):
            log.warning( 'Request tries to access a file outside of the repository location. File path: %s', abs_file_path )
            return 'Invalid file path'
        if os.path.islink( abs_file_path ):
            safe_str = 'link to: ' + basic_util.to_html_string( os.readlink( abs_file_path ) )
            return safe_str
        elif checkers.is_gzip( abs_file_path ):
            return '<br/>gzip compressed file<br/>'
        elif checkers.is_bz2( abs_file_path ):
            return '<br/>bz2 compressed file<br/>'
        elif checkers.check_zip( abs_file_path ):
            return '<br/>zip compressed file<br/>'
        elif checkers.check_binary( abs_file_path ):
            return '<br/>Binary file<br/>'
        else:
            for i, line in enumerate( open( abs_file_path ) ):
                safe_str = '%s%s' % ( safe_str, basic_util.to_html_string( line ) )
                # Stop reading after string is larger than MAX_CONTENT_SIZE.
                if len( safe_str ) > MAX_CONTENT_SIZE:
                    large_str = \
                        '<br/>File contents truncated because file size is larger than maximum viewing size of %s<br/>' % \
                        util.nice_size( MAX_CONTENT_SIZE )
                    safe_str = '%s%s' % ( safe_str, large_str )
                    break

            if len( safe_str ) > basic_util.MAX_DISPLAY_SIZE:
                # Eliminate the middle of the file to display a file no larger than basic_util.MAX_DISPLAY_SIZE.
                # This may not be ideal if the file is larger than MAX_CONTENT_SIZE.
                join_by_str = \
                    "<br/><br/>...some text eliminated here because file size is larger than maximum viewing size of %s...<br/><br/>" % \
                    util.nice_size( basic_util.MAX_DISPLAY_SIZE )
                safe_str = util.shrink_string_by_size( safe_str,
                                                       basic_util.MAX_DISPLAY_SIZE,
                                                       join_by=join_by_str,
                                                       left_larger=True,
                                                       beginning_on_size_error=True )
            return safe_str

    def is_path_browsable( self, app, path, repo ):
        """
        Detects whether the given path is browsable i.e. is within the
        given repository folders or tool dependencies.

        :param  path:      any file path
        :type   path:      str
        :param  repo:      repository to check against
        :type   repo:      ToolShedRepository

        :returns:   True in case path is within repo or tool_dependency_dir
        :rtype:     bool
        """
        return self.is_path_within_repo( app, path, repo) or self.is_path_within_dependency_dir( app, path )

    def is_path_within_dependency_dir( self, app, path ):
        """
        Detect whether the given path is within the tool_dependency_dir folder on the disk.
        (Specified by the config option). Use to filter malicious symlinks targeting outside paths.

        :param  path:      any file path
        :type   path:      str

        :returns:   True in case path is within dependency_dir
        :rtype:     bool
        """
        is_within = False
        resolved_path = os.path.realpath( path )
        tool_dependency_dir = app.config.get( 'tool_dependency_dir', None )
        if tool_dependency_dir:
            dependency_path = os.path.abspath( tool_dependency_dir )
            is_within = os.path.commonprefix( [ dependency_path, resolved_path ] ) == dependency_path
        return is_within

    def is_path_within_repo( self, app, path, repo ):
        """
        Detect whether the given path is within the repository folder on the disk.
        Use to filter malicious symlinks targeting outside paths.

        :param  path:      any file path
        :type   path:      str
        :param  repo:      repository to check against
        :type   repo:      ToolShedRepository

        :returns:   True in case path is within the given repo's folder
        :rtype:     bool
        """
        repo_path = os.path.abspath( repo.repo_path( app, repo.changeset_revision ) )
        resolved_path = os.path.realpath( path )
        return os.path.commonprefix( [ repo_path, resolved_path ] ) == repo_path

    def __create_jstree( self, directory ):
        """
        Load recursively all files and folders within the given folder
        and its subfolders and returns jstree representation
        of its structure.
        Ignores .hg/ folder.

        :param  directory:      path to dir to create jstree representation of
        :type   directory:      str

        :returns:   jstree representation of a given folder
        :rtype:     JSTree object
        """
        dir_jstree = None
        jstree_paths = []
        if os.path.exists( directory ):
            for ( dirpath, dirnames, filenames ) in os.walk( directory ):
                for dirname in dirnames:
                    dir_path = os.path.relpath( os.path.join( dirpath, dirname ), directory )
                    if dir_path.startswith( '.hg' ):
                        continue
                    dir_path_hash = hashlib.sha1(unicodify(dir_path).encode('utf-8')).hexdigest()
                    jstree_paths.append( jstree.Path( dir_path, dir_path_hash, { 'type': 'folder', 'li_attr': { 'full_path': dir_path } } ) )

                for filename in filenames:
                    file_path = os.path.relpath( os.path.join( dirpath, filename ), directory )
                    if file_path.startswith( '.hg' ):
                        continue
                    file_path_hash = hashlib.sha1(unicodify(file_path).encode('utf-8')).hexdigest()
                    jstree_paths.append( jstree.Path( file_path, file_path_hash, { 'type': 'file', 'li_attr': { 'full_path': file_path } } ) )
        else:
            raise exceptions.ConfigDoesNotAllowException( 'The given directory does not exist.' )
        dir_jstree = jstree.JSTree( jstree_paths )
        return dir_jstree


class RepositorySerializer( base.ModelSerializer ):
    model_manager_class = RepoManager

    def __init__( self, app ):
        """
        Convert a Repository and associated data to a dictionary representation.
        """
        super( RepositorySerializer, self ).__init__( app )
        self.user_manager = self.manager

        self.default_view = 'summary'
        self.add_view( 'summary', [
            'id',
            'name',
            'owner',
            'status',
            'create_time',
            'tool_shed',
            'tool_shed_status',
            'ctx_rev',

        ])
        self.add_view( 'detailed', [
            'uninstalled',
            'description',
            'deleted',
            'error_message',
            'changeset_revision',
            'installed_changeset_revision',
            'update_time',
            'includes_datatypes',
            'dist_to_shed',
        ], include_keys_from='summary' )

    def add_serializers( self ):
        super( RepositorySerializer, self ).add_serializers()

        self.serializers.update({
            'id': self.serialize_id,
            'create_time': self.serialize_interval,
            'update_time': self.serialize_date,
        })

    def serialize_interval( self, item, key, **context ):
        date = getattr( item, key )
        return { 'interval': pretty_print_time_interval( date, precise=True ), 'date': self.serialize_date( item, key ) }
