import os

from .framework import SeleniumIntegrationTestCase

TRS_CONFIG = """
- api_url: https://dockstore.org/api
  doc: 'Dockstore is an open platform used by the GA4GH for sharing Docker-based tools
    and workflows.'
  id: dockstore
  label: dockstore
  link_url: https://dockstore.org
- api_url: https://workflowhub.eu
  doc: 'WorkflowHub is a registry of scientific workflows.'
  id: workflowhub
  label: workflowhub
  link_url: https://workflowhub.eu
"""
TRS_ID_DOCKSTORE = (
    "workflow/github.com/iwc-workflows/sars-cov-2-pe-illumina-artic-variant-calling/COVID-19-PE-ARTIC-ILLUMINA"
)
TRS_NAME = "sars-cov-2-pe-illumina-artic-variant-calling/COVID-19-PE-ARTIC-ILLUMINA"
TRS_VERSION_DOCKSTORE = "v0.4"
TRS_ID_WORKFLOWHUB = "110"
TRS_VERSION_WORKFLOWHUB = "4"
WORKFLOW_NAME = "COVID-19: variation analysis on ARTIC PE data"


class TrsImportTestCase(SeleniumIntegrationTestCase):
    ensure_registered = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        trs_config_dir = cls.trs_config_dir()
        os.makedirs(trs_config_dir)
        trs_config_file = os.path.join(trs_config_dir, "trs_config.yml")
        with open(trs_config_file, "w") as trs_config:
            trs_config.write(TRS_CONFIG)
        config["trs_servers_config_file"] = trs_config_file

    @classmethod
    def trs_config_dir(cls):
        return cls.temp_config_dir("trs")

    def assert_workflow_imported(self, name):
        self.workflow_index_search_for(name)
        assert len(self.workflow_index_table_elements()) == 1, f"workflow ${name} not imported"

    def test_import_workflow_by_url_dockstore(self):
        import_url = f"workflows/trs_import?trs_server=dockstore.org&trs_version={TRS_VERSION_DOCKSTORE}&trs_id=%23{TRS_ID_DOCKSTORE}"
        self._import_workflow_by_url(import_url)

    def test_import_workflow_by_url_workflowhub(self):
        import_url = f"workflows/trs_import?trs_server=workflowhub&trs_version={TRS_VERSION_WORKFLOWHUB}&trs_id={TRS_ID_WORKFLOWHUB}"
        self._import_workflow_by_url(import_url)

    def _import_workflow_by_url(self, import_url):
        full_url = self.build_url(import_url)
        self.driver.get(full_url)
        self.components.workflows.workflow_table.wait_for_visible()
        self.assert_workflow_imported(WORKFLOW_NAME)

    def test_import_by_search_dockstore(self):
        self.go_to_trs_search()
        self.components.trs_search.search.wait_for_and_send_keys("This is the documentation for the workflow.")
        self.components.trs_search.search_result(
            workflow_name="galaxy-workflow-dockstore-example-1"
        ).wait_for_and_click()
        self.components.trs_search.import_button.wait_for_and_click()
        self.sleep_for(self.wait_types.UX_RENDER)
        self.workflow_index_open()
        self.assert_workflow_imported("Test Workflow")

    def test_import_by_organization_search_dockstore(self):
        self.go_to_trs_search()
        self.components.trs_search.search.wait_for_and_send_keys("organization: iwc-workflows")
        self.components.trs_search.search_result(workflow_name=TRS_NAME).wait_for_and_click()
        self.components.trs_search.import_version(version="v0.4").wait_for_and_click()
        self.sleep_for(self.wait_types.UX_RENDER)
        self.workflow_index_open()
        self.assert_workflow_imported(WORKFLOW_NAME)
        self.components.workflows.trs_icon.wait_for_visible()
        self.screenshot("workflow_imported_via_dockstore_search")

    def test_import_by_search_workflowhub(self):
        self.go_to_trs_search()
        self.components.trs_search.select_server_button.wait_for_and_click()
        self.components.trs_search.select_server(server="workflowhub").wait_for_and_click()
        self.components.trs_search.search.wait_for_and_send_keys(WORKFLOW_NAME)
        self.components.trs_search.search_result(workflow_name=WORKFLOW_NAME).wait_for_and_click()
        self.components.trs_search.import_button.wait_for_and_click()
        self.sleep_for(self.wait_types.UX_RENDER)
        self.workflow_index_open()
        self.assert_workflow_imported(WORKFLOW_NAME)

    def test_import_by_id_dockstore(self):
        self._import_by_id(f"#{TRS_ID_DOCKSTORE}", server="dockstore")

    def test_import_by_id_workflowhub(self):
        self._import_by_id(TRS_ID_WORKFLOWHUB, server="workflowhub")

    def _import_by_id(self, trs_id, server):
        self.go_to_trs_by_id()
        self.components.trs_import.select_server_button.wait_for_and_click()
        self.components.trs_import.select_server(server=server).wait_for_and_click()
        self.components.trs_import.input.wait_for_and_send_keys(trs_id)
        self.components.trs_import.import_version(version="v0.4").wait_for_and_click()
        self.sleep_for(self.wait_types.UX_RENDER)
        self.workflow_index_open()
        self.assert_workflow_imported(WORKFLOW_NAME)
