import logging
from datetime import datetime
from time import gmtime
from time import strftime

from galaxy import eggs
eggs.require( 'mercurial' )

from mercurial import cmdutil
from mercurial import commands
from mercurial import hg
from mercurial import ui

def get_changectx_for_changeset( repo, changeset_revision, **kwd ):
    """Retrieve a specified changectx from a repository."""
    for changeset in repo.changelog:
        ctx = repo.changectx( changeset )
        if str( ctx ) == changeset_revision:
            return ctx
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
    
def get_readable_ctx_date( ctx ):
    """Convert the date of the changeset (the received ctx) to a human-readable date."""
    t, tz = ctx.date()
    date = datetime( *gmtime( float( t ) - tz )[ :6 ] )
    ctx_date = date.strftime( "%Y-%m-%d" )
    return ctx_date

def get_revision_label( trans, repository, changeset_revision, include_date=True, include_hash=True ):
    """
    Return a string consisting of the human read-able changeset rev and the changeset revision string
    which includes the revision date if the receive include_date is True.
    """
    repo = hg.repository( get_configured_ui(), repository.repo_path( trans.app ) )
    ctx = get_changectx_for_changeset( repo, changeset_revision )
    if ctx:
        return get_revision_label_from_ctx( ctx, include_date=include_date, include_hash=include_hash )
    else:
        if include_hash:
            return "-1:%s" % changeset_revision
        else:
            return "-1"

def get_rev_label_changeset_revision_from_repository_metadata( trans, repository_metadata, repository=None,
                                                               include_date=True, include_hash=True ):
    if repository is None:
        repository = repository_metadata.repository
    repo = hg.repository( get_configured_ui(), repository.repo_path( trans.app ) )
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
