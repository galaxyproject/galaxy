import os
from collections import namedtuple

from base import integration_util
from base.populators import DatasetPopulator

from tool_shed.util import hg_util
from .uses_shed import UsesShed

REPO = namedtuple('Repository', 'name owner changeset')(
    'collection_column_join',
    'iuc',
    'dfde09461b1e',  # revision 2, a known installable revision
)
REVISION_3 = '58228a4d58fe'
REVISION_4 = '071084070619'


class TestRepositoryInstallIntegrationTestCase(integration_util.IntegrationTestCase, UsesShed):

    """Test data manager installation and table reload through the API"""

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        cls.configure_shed(config)

    def setUp(self):
        super(TestRepositoryInstallIntegrationTestCase, self).setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    def tearDown(self):
        self.reset_shed_tools()

    def test_repository_installation(self):
        """
        Test that we can install a given revision.
        """
        self._install_repository()

    def test_repository_uninstall(self):
        """Test that we can uninstall a repository"""
        self._install_repository()
        self._uninstall_repository()

    def test_repository_update(self):
        response = self._install_repository(revision=REVISION_4, version="0.0.3")[0]
        assert response['ctx_rev'] == '4'
        repo_response = self._get("/api/tool_shed_repositories/%s" % response['id']).json()
        assert repo_response['tool_shed_status']['revision_update'] == 'False'  # that should really be a boolean
        # now checkout revision 3 and attempt an update
        path_components = [
            self._app.config.shed_tools_dir,
            'toolshed.g2.bx.psu.edu',
            'repos',
            REPO.owner,
            REPO.name,
            REVISION_3,
            REPO.name
        ]
        revision_3_path = os.path.join(*path_components[:6])
        revision_4_path = os.path.join(*path_components[:5] + [REVISION_4])
        repository_path = os.path.join(*path_components)
        # Move repo to location expected before minor update
        os.rename(revision_4_path, revision_3_path)
        # Checkout revision 3
        hg_util.update_repository(repository_path, ctx_rev='3')
        # change repo to revision 3 in database
        model = self._app.install_model
        tsr = model.context.query(model.ToolShedRepository).first()
        assert tsr.name == REPO.name
        assert tsr.changeset_revision == REVISION_4
        assert tsr.ctx_rev == '4'
        tsr.ctx_rev = '3'
        tsr.installed_changeset_revision = REVISION_3
        tsr.changeset_revision = REVISION_3
        model.context.flush()
        # update shed_tool_conf.xml to look like revision 3 was the installed_changeset_revision
        with open(self._app.config.shed_tool_config_file) as shed_config:
            shed_text = shed_config.read().replace(REVISION_4, REVISION_3)
        with open(self._app.config.shed_tool_config_file, 'w') as shed_config:
            shed_config.write(shed_text)
        self._get('/api/tool_shed_repositories/check_for_updates', data={'id': response['id']}).json()
        # At this point things should look like there is minor update available
        repo_response = self._get("/api/tool_shed_repositories/%s" % response['id']).json()
        assert repo_response['tool_shed_status']['revision_update'] == 'True'
        assert repo_response['changeset_revision'] == REVISION_3
        assert repo_response['ctx_rev'] == '3'
        # now install revision 4 (a.k.a a minor update)
        response = self._install_repository(revision=REVISION_4, version="0.0.3", verify_tool_absent=False)[0]
        assert response['changeset_revision'] == REVISION_4
        assert response['installed_changeset_revision'] == REVISION_3
        assert response['ctx_rev'] == '4'

    def _uninstall_repository(self):
        tool = self._get('/api/tools/collection_column_join').json()
        assert tool['version'] == "0.0.2"
        self.uninstall_repository(REPO.owner, REPO.name, REPO.changeset)
        response = self._get('/api/tools/collection_column_join').json()
        assert response['err_msg']

    def _install_repository(self, revision=None, version="0.0.2", verify_tool_absent=True):
        if verify_tool_absent:
            response = self._get('/api/tools/collection_column_join').json()
            assert response['err_msg']
        install_response = self.install_repository(REPO.owner, REPO.name, revision or REPO.changeset)
        tool = self._get('/api/tools/collection_column_join').json()
        assert tool['version'] == version
        return install_response
