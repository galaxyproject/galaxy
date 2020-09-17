import logging

from mercurial.hgweb.hgwebdir_mod import hgwebdir
from mercurial.hgweb.request import wsgiapplication

from galaxy import web
from galaxy.exceptions import ObjectNotFound
from galaxy.webapps.base.controller import BaseUIController
from tool_shed.util.repository_util import get_repository_by_name_and_owner

log = logging.getLogger(__name__)


class HgController(BaseUIController):
    @web.expose
    def handle_request(self, trans, **kwd):
        # The os command that results in this method being called will look something like:
        # hg clone http://test@127.0.0.1:9009/repos/test/convert_characters1
        hgweb_config = trans.app.hgweb_config_manager.hgweb_config

        def make_web_app():
            hgwebapp = hgwebdir(hgweb_config.encode('utf-8'))
            return hgwebapp

        wsgi_app = wsgiapplication(make_web_app)
        repository = None
        path_info = kwd.get('path_info', None)
        if path_info and len(path_info.split('/')) == 2:
            owner, name = path_info.split('/')
            repository = get_repository_by_name_and_owner(trans.app, name, owner)
        if repository:
            if repository.deprecated:
                raise ObjectNotFound("Requested repository not found or deprecated.")
            cmd = kwd.get('cmd', None)
            if cmd == 'getbundle':
                times_downloaded = repository.times_downloaded
                times_downloaded += 1
                repository.times_downloaded = times_downloaded
                trans.sa_session.add(repository)
                trans.sa_session.flush()
        return wsgi_app
