import logging
from galaxy import web
from galaxy.web.base.controller import BaseUIController

from tool_shed.util.common_util import generate_clone_url_for_repository_in_tool_shed
from tool_shed.util.shed_util_common import get_repository_by_name_and_owner
from tool_shed.util.hg_util import update_repository
from tool_shed.metadata import repository_metadata_manager

import mercurial.__version__
from mercurial.hgweb.hgwebdir_mod import hgwebdir
from mercurial import hg
from mercurial import ui

log = logging.getLogger(__name__)


class HgController( BaseUIController ):

    @web.expose
    def handle_request( self, trans, owner, name, **kwd ):
        # The os command that results in this method being called will look something like:
        # hg clone http://test@127.0.0.1:9009/repos/test/convert_characters1
        hg_version = mercurial.__version__.version
        cmd = kwd.get( 'cmd', None )
        hgweb_config = trans.app.hgweb_config_manager.hgweb_config
        repository = get_repository_by_name_and_owner( trans.app, name, owner )
        if repository:
            repo = hg.repository( ui.ui(), repository.repo_path( trans.app ) )
        if hg_version >= '2.2.3' and cmd == 'pushkey' and repository:
            # When doing an "hg push" from the command line, the following commands, in order, will be
            # retrieved from environ, depending upon the mercurial version being used.  In mercurial
            # version 2.2.3, section 15.2. Command changes includes a new feature:
            # pushkey: add hooks for pushkey/listkeys
            # (see http://mercurial.selenic.com/wiki/WhatsNew#Mercurial_2.2.3_.282012-07-01.29).
            # We require version 2.2.3 since the pushkey hook was added in that version.
            # If mercurial version >= '2.2.3': capabilities -> batch -> branchmap -> unbundle -> listkeys -> pushkey
            # Update the repository on disk to the tip revision, because the web upload
            # form uses the on-disk working directory. If the repository is not updated
            # on disk, pushing from the command line and then uploading  via the web
            # interface will result in a new head being created.
            update_repository( repo, ctx_rev=None )
            # Set metadata using the repository files on disk.
            repository_clone_url = generate_clone_url_for_repository_in_tool_shed( trans.user, repository )
            rmm = repository_metadata_manager.RepositoryMetadataManager( app=trans.app,
                                                                         user=trans.user,
                                                                         repository=repository,
                                                                         changeset_revision=repository.tip( trans.app ),
                                                                         repository_clone_url=repository_clone_url,
                                                                         relative_install_dir=repository.repo_path( trans.app ),
                                                                         repository_files_dir=None,
                                                                         resetting_all_metadata_on_repository=False,
                                                                         updating_installed_repository=False,
                                                                         persist=False )
            error_message, status = rmm.set_repository_metadata( trans.request.host )
            if status == 'ok' and error_message:
                log.debug( "Successfully reset metadata on repository %s owned by %s, but encountered problem: %s" %
                           ( str( repository.name ), str( repository.user.username ), error_message ) )
            elif status != 'ok' and error_message:
                log.debug( "Error resetting metadata on repository %s owned by %s: %s" %
                           ( str( repository.name ), str( repository.user.username ), error_message ) )
        return hgwebdir( hgweb_config )
