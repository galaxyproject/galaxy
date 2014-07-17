import json
import logging
import os
import struct

from datetime import datetime
from time import gmtime
from time import strftime
import tempfile

from galaxy.util import listify
from galaxy import eggs
eggs.require( 'mercurial' )

from mercurial import cmdutil
from mercurial import commands
from mercurial import hg
from mercurial import ui
from mercurial.changegroup import readbundle
from mercurial.changegroup import readexactly

from tool_shed.util import basic_util

log = logging.getLogger( __name__ )

INITIAL_CHANGELOG_HASH = '000000000000'

def add_changeset( repo_ui, repo, path_to_filename_in_archive ):
    commands.add( repo_ui, repo, path_to_filename_in_archive )

def archive_repository_revision( app, repository, archive_dir, changeset_revision ):
    '''Create an un-versioned archive of a repository.'''
    repo = get_repo_for_repository( app, repository=repository, repo_path=None, create=False )
    options_dict = get_mercurial_default_options_dict( 'archive' )
    options_dict[ 'rev' ] = changeset_revision
    error_message = ''
    return_code = None
    try:
        return_code = commands.archive( get_configured_ui, repo, archive_dir, **options_dict )
    except Exception, e:
        error_message = "Error attempting to archive revision <b>%s</b> of repository %s: %s\nReturn code: %s\n" % \
            ( str( changeset_revision ), str( repository.name ), str( e ), str( return_code ) )
        log.exception( error_message )
    return return_code, error_message

def bundle_to_json( fh ):
    """
    Convert the received HG10xx data stream (a mercurial 1.0 bundle created using hg push from the
    command line) to a json object.
    """
    # See http://www.wstein.org/home/wstein/www/home/was/patches/hg_json
    hg_unbundle10_obj = readbundle( fh, None )
    groups = [ group for group in unpack_groups( hg_unbundle10_obj ) ]
    return json.dumps( groups, indent=4 )

def clone_repository( repository_clone_url, repository_file_dir, ctx_rev ):
    """
    Clone the repository up to the specified changeset_revision.  No subsequent revisions will be
    present in the cloned repository.
    """
    try:
        commands.clone( get_configured_ui(),
                        str( repository_clone_url ),
                        dest=str( repository_file_dir ),
                        pull=True,
                        noupdate=False,
                        rev=listify( str( ctx_rev ) ) )
        return True, None
    except Exception, e:
        error_message = 'Error cloning repository: %s' % str( e )
        log.debug( error_message )
        return False, error_message

def commit_changeset( repo_ui, repo, full_path_to_changeset, username, message ):
    commands.commit( repo_ui, repo, full_path_to_changeset, user=username, message=message )

def copy_file_from_manifest( repo, ctx, filename, dir ):
    """
    Copy the latest version of the file named filename from the repository manifest to the directory
    to which dir refers.
    """
    for changeset in reversed_upper_bounded_changelog( repo, ctx ):
        changeset_ctx = repo.changectx( changeset )
        fctx = get_file_context_from_ctx( changeset_ctx, filename )
        if fctx and fctx not in [ 'DELETED' ]:
            file_path = os.path.join( dir, filename )
            fh = open( file_path, 'wb' )
            fh.write( fctx.data() )
            fh.close()
            return file_path
    return None

def create_hgrc_file( app, repository ):
    # At this point, an entry for the repository is required to be in the hgweb.config
    # file so we can call repository.repo_path( trans.app ).  Since we support both
    # http and https, we set push_ssl to False to override the default (which is True)
    # in the mercurial api.  The hg purge extension purges all files and directories
    # not being tracked by mercurial in the current repository.  It'll remove unknown
    # files and empty directories.  This is not currently used because it is not supported
    #in the mercurial API.
    repo = get_repo_for_repository( app, repository=repository, repo_path=None, create=False )
    fp = repo.opener( 'hgrc', 'wb' )
    fp.write( '[paths]\n' )
    fp.write( 'default = .\n' )
    fp.write( 'default-push = .\n' )
    fp.write( '[web]\n' )
    fp.write( 'allow_push = %s\n' % repository.user.username )
    fp.write( 'name = %s\n' % repository.name )
    fp.write( 'push_ssl = false\n' )
    fp.write( '[extensions]\n' )
    fp.write( 'hgext.purge=' )
    fp.close()

def get_changectx_for_changeset( repo, changeset_revision, **kwd ):
    """Retrieve a specified changectx from a repository."""
    for changeset in repo.changelog:
        ctx = repo.changectx( changeset )
        if str( ctx ) == changeset_revision:
            return ctx
    return None

def get_config( config_file, repo, ctx, dir ):
    """Return the latest version of config_filename from the repository manifest."""
    config_file = basic_util.strip_path( config_file )
    for changeset in reversed_upper_bounded_changelog( repo, ctx ):
        changeset_ctx = repo.changectx( changeset )
        for ctx_file in changeset_ctx.files():
            ctx_file_name = basic_util.strip_path( ctx_file )
            if ctx_file_name == config_file:
                return get_named_tmpfile_from_ctx( changeset_ctx, ctx_file, dir )
    return None

def get_config_from_disk( config_file, relative_install_dir ):
    for root, dirs, files in os.walk( relative_install_dir ):
        if root.find( '.hg' ) < 0:
            for name in files:
                if name == config_file:
                    return os.path.abspath( os.path.join( root, name ) )
    return None

def get_configured_ui():
    """Configure any desired ui settings."""
    _ui = ui.ui()
    # The following will suppress all messages.  This is
    # the same as adding the following setting to the repo
    # hgrc file' [ui] section:
    # quiet = True
    _ui.setconfig( 'ui', 'quiet', True )
    return _ui

def get_ctx_file_path_from_manifest( filename, repo, changeset_revision ):
    """
    Get the ctx file path for the latest revision of filename from the repository manifest up
    to the value of changeset_revision.
    """
    stripped_filename = basic_util.strip_path( filename )
    for changeset in reversed_upper_bounded_changelog( repo, changeset_revision ):
        manifest_changeset_revision = str( repo.changectx( changeset ) )
        manifest_ctx = repo.changectx( changeset )
        for ctx_file in manifest_ctx.files():
            ctx_file_name = basic_util.strip_path( ctx_file )
            if ctx_file_name == stripped_filename:
                return manifest_ctx, ctx_file
    return None, None

def get_file_context_from_ctx( ctx, filename ):
    """Return the mercurial file context for a specified file."""
    # We have to be careful in determining if we found the correct file because multiple files with
    # the same name may be in different directories within ctx if the files were moved within the change
    # set.  For example, in the following ctx.files() list, the former may have been moved to the latter: 
    # ['tmap_wrapper_0.0.19/tool_data_table_conf.xml.sample', 'tmap_wrapper_0.3.3/tool_data_table_conf.xml.sample'].
    # Another scenario is that the file has been deleted.
    deleted = False
    filename = basic_util.strip_path( filename )
    for ctx_file in ctx.files():
        ctx_file_name = basic_util.strip_path( ctx_file )
        if filename == ctx_file_name:
            try:
                # If the file was moved, its destination will be returned here.
                fctx = ctx[ ctx_file ]
                return fctx
            except LookupError, e:
                # Set deleted for now, and continue looking in case the file was moved instead of deleted.
                deleted = True
    if deleted:
        return 'DELETED'
    return None

def get_mercurial_default_options_dict( command, command_table=None, **kwd ):
    '''Borrowed from repoman - get default parameters for a mercurial command.'''
    if command_table is None:
        command_table = commands.table
    possible = cmdutil.findpossible( command, command_table )
    if len( possible ) != 1:
        raise Exception, 'unable to find mercurial command "%s"' % command
    default_options_dict = dict( ( r[ 1 ].replace( '-', '_' ), r[ 2 ] ) for r in possible[ possible.keys()[ 0 ] ][ 1 ][ 1 ] )
    for option in kwd:
        default_options_dict[ option ] = kwd[ option ]
    return default_options_dict

def get_named_tmpfile_from_ctx( ctx, filename, dir ):
    """
    Return a named temporary file created from a specified file with a given name included in a repository
    changeset revision.
    """
    filename = basic_util.strip_path( filename )
    for ctx_file in ctx.files():
        ctx_file_name = basic_util.strip_path( ctx_file )
        if filename == ctx_file_name:
            try:
                # If the file was moved, its destination file contents will be returned here.
                fctx = ctx[ ctx_file ]
            except LookupError, e:
                # Continue looking in case the file was moved.
                fctx = None
                continue
            if fctx:
                fh = tempfile.NamedTemporaryFile( 'wb', prefix="tmp-toolshed-gntfc", dir=dir )
                tmp_filename = fh.name
                fh.close()
                fh = open( tmp_filename, 'wb' )
                fh.write( fctx.data() )
                fh.close()
                return tmp_filename
    return None

def get_readable_ctx_date( ctx ):
    """Convert the date of the changeset (the received ctx) to a human-readable date."""
    t, tz = ctx.date()
    date = datetime( *gmtime( float( t ) - tz )[ :6 ] )
    ctx_date = date.strftime( "%Y-%m-%d" )
    return ctx_date

def get_repo_for_repository( app, repository=None, repo_path=None, create=False ):
    if repository is not None:
        return hg.repository( get_configured_ui(), repository.repo_path( app ), create=create )
    if repo_path is not None:
        return hg.repository( get_configured_ui(), repo_path, create=create )

def get_repository_heads( repo ):
    """Return current repository heads, which are changesets with no child changesets."""
    heads = [ repo[ h ] for h in repo.heads( None ) ]
    return heads

def get_reversed_changelog_changesets( repo ):
    """Return a list of changesets in reverse order from that provided by the repository manifest."""
    reversed_changelog = []
    for changeset in repo.changelog:
        reversed_changelog.insert( 0, changeset )
    return reversed_changelog

def get_revision_label( app, repository, changeset_revision, include_date=True, include_hash=True ):
    """
    Return a string consisting of the human read-able changeset rev and the changeset revision string
    which includes the revision date if the receive include_date is True.
    """
    repo = get_repo_for_repository( app, repository=repository, repo_path=None )
    ctx = get_changectx_for_changeset( repo, changeset_revision )
    if ctx:
        return get_revision_label_from_ctx( ctx, include_date=include_date, include_hash=include_hash )
    else:
        if include_hash:
            return "-1:%s" % changeset_revision
        else:
            return "-1"

def get_rev_label_changeset_revision_from_repository_metadata( app, repository_metadata, repository=None,
                                                               include_date=True, include_hash=True ):
    if repository is None:
        repository = repository_metadata.repository
    repo = hg.repository( get_configured_ui(), repository.repo_path( app ) )
    changeset_revision = repository_metadata.changeset_revision
    ctx = get_changectx_for_changeset( repo, changeset_revision )
    if ctx:
        rev = '%04d' % ctx.rev()
        if include_date:
            changeset_revision_date = get_readable_ctx_date( ctx )
            if include_hash:
                label = "%s:%s (%s)" % ( str( ctx.rev() ), changeset_revision, changeset_revision_date )
            else:
                label = "%s (%s)" % ( str( ctx.rev() ), changeset_revision_date )
        else:
            if include_hash:
                label = "%s:%s" % ( str( ctx.rev() ), changeset_revision )
            else:
                label = "%s" % str( ctx.rev() )
    else:
        rev = '-1'
        if include_hash:
            label = "-1:%s" % changeset_revision
        else:
            label = "-1"
    return rev, label, changeset_revision

def get_revision_label_from_ctx( ctx, include_date=True, include_hash=True ):
    if include_date:
        if include_hash:
            return '%s:%s <i><font color="#666666">(%s)</font></i>' % \
                ( str( ctx.rev() ), str( ctx ), str( get_readable_ctx_date( ctx ) ) )
        else:
            return '%s <i><font color="#666666">(%s)</font></i>' % \
                ( str( ctx.rev() ), str( get_readable_ctx_date( ctx ) ) )
    else:
        if include_hash:
            return '%s:%s' % ( str( ctx.rev() ), str( ctx ) )
        else:
            return '%s' % str( ctx.rev() )

def get_rev_label_from_changeset_revision( repo, changeset_revision, include_date=True, include_hash=True ):
    """
    Given a changeset revision hash, return two strings, the changeset rev and the changeset revision hash
    which includes the revision date if the receive include_date is True.
    """
    ctx = get_changectx_for_changeset( repo, changeset_revision )
    if ctx:
        rev = '%04d' % ctx.rev()
        label = get_revision_label_from_ctx( ctx, include_date=include_date )
    else:
        rev = '-1'
        label = "-1:%s" % changeset_revision
    return rev, label

def pull_repository( repo, repository_clone_url, ctx_rev ):
    """Pull changes from a remote repository to a local one."""
    commands.pull( get_configured_ui(), repo, source=repository_clone_url, rev=[ ctx_rev ] )

def remove_file( repo_ui, repo, selected_file, force=True ):
    commands.remove( repo_ui, repo, selected_file, force=force )

def reversed_lower_upper_bounded_changelog( repo, excluded_lower_bounds_changeset_revision, included_upper_bounds_changeset_revision ):
    """
    Return a reversed list of changesets in the repository changelog after the excluded_lower_bounds_changeset_revision,
    but up to and including the included_upper_bounds_changeset_revision.  The value of excluded_lower_bounds_changeset_revision
    will be the value of INITIAL_CHANGELOG_HASH if no valid changesets exist before included_upper_bounds_changeset_revision.
    """
    # To set excluded_lower_bounds_changeset_revision, calling methods should do the following, where the value
    # of changeset_revision is a downloadable changeset_revision.
    # excluded_lower_bounds_changeset_revision = \
    #     metadata_util.get_previous_metadata_changeset_revision( repository, repo, changeset_revision, downloadable=? )
    if excluded_lower_bounds_changeset_revision == INITIAL_CHANGELOG_HASH:
        appending_started = True
    else:
        appending_started = False
    reversed_changelog = []
    for changeset in repo.changelog:
        changeset_hash = str( repo.changectx( changeset ) )
        if appending_started:
            reversed_changelog.insert( 0, changeset )
        if changeset_hash == excluded_lower_bounds_changeset_revision and not appending_started:
            appending_started = True
        if changeset_hash == included_upper_bounds_changeset_revision:
            break
    return reversed_changelog

def reversed_upper_bounded_changelog( repo, included_upper_bounds_changeset_revision ):
    """
    Return a reversed list of changesets in the repository changelog up to and including the
    included_upper_bounds_changeset_revision.
    """
    return reversed_lower_upper_bounded_changelog( repo, INITIAL_CHANGELOG_HASH, included_upper_bounds_changeset_revision )

def unpack_chunks( hg_unbundle10_obj ):
    """
    This method provides a generator of parsed chunks of a "group" in a mercurial unbundle10 object which
    is created when a changeset that is pushed to a Tool Shed repository using hg push from the command line
    is read using readbundle.
    """
    while True:
        length, = struct.unpack( '>l', readexactly( hg_unbundle10_obj, 4 ) )
        if length <= 4:
            # We found a "null chunk", which ends the group.
            break
        if length < 84:
            raise Exception( "negative data length" )
        node, p1, p2, cs = struct.unpack( '20s20s20s20s', readexactly( hg_unbundle10_obj, 80 ) )
        yield { 'node': node.encode( 'hex' ),
                'p1': p1.encode( 'hex' ),
                'p2': p2.encode( 'hex' ),
                'cs': cs.encode( 'hex' ),
                'data': [ patch for patch in unpack_patches( hg_unbundle10_obj, length - 84 ) ] }

def unpack_groups( hg_unbundle10_obj ):
    """
    This method provides a generator of parsed groups from a mercurial unbundle10 object which is
    created when a changeset that is pushed to a Tool Shed repository using hg push from the command
    line is read using readbundle.
    """
    # Process the changelog group.
    yield [ chunk for chunk in unpack_chunks( hg_unbundle10_obj ) ]
    # Process the manifest group.
    yield [ chunk for chunk in unpack_chunks( hg_unbundle10_obj ) ]
    while True:
        length, = struct.unpack( '>l', readexactly( hg_unbundle10_obj, 4 ) )
        if length <= 4:
            # We found a "null meta chunk", which ends the changegroup.
            break
        filename = readexactly( hg_unbundle10_obj, length-4 ).encode( 'string_escape' )
        # Process the file group.
        yield ( filename, [ chunk for chunk in unpack_chunks( hg_unbundle10_obj ) ] )

def unpack_patches( hg_unbundle10_obj, remaining ):
    """
    This method provides a generator of patches from the data field in a chunk. As there is no delimiter
    for this data field, a length argument is required.
    """
    while remaining >= 12:
        start, end, blocklen = struct.unpack( '>lll', readexactly( hg_unbundle10_obj, 12 ) )
        remaining -= 12
        if blocklen > remaining:
            raise Exception( "unexpected end of patch stream" )
        block = readexactly( hg_unbundle10_obj, blocklen )
        remaining -= blocklen
        yield { 'start': start,
                'end': end,
                'blocklen': blocklen,
                'block': block.encode( 'string_escape' ) }
    if remaining > 0:
        print remaining
        raise Exception( "unexpected end of patch stream" )

def update_repository( repo, ctx_rev=None ):
    """
    Update the cloned repository to changeset_revision.  It is critical that the installed repository is updated to the desired
    changeset_revision before metadata is set because the process for setting metadata uses the repository files on disk.
    """
    # TODO: We may have files on disk in the repo directory that aren't being tracked, so they must be removed.
    # The codes used to show the status of files are as follows.
    # M = modified
    # A = added
    # R = removed
    # C = clean
    # ! = deleted, but still tracked
    # ? = not tracked
    # I = ignored
    # It would be nice if we could use mercurial's purge extension to remove untracked files.  The problem is that
    # purging is not supported by the mercurial API.
    commands.update( get_configured_ui(), repo, rev=ctx_rev )
