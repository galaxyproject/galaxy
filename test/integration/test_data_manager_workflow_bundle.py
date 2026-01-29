"""Integration tests for workflow syncing."""

from galaxy_test.base.populators import (
    DatasetPopulator,
    WorkflowPopulator,
)
from galaxy_test.base.uses_shed_api import UsesShedApi
from .test_containerized_jobs import ContainerizedIntegrationTestCase


class TestDataManagerWorkflowInvocation(ContainerizedIntegrationTestCase, UsesShedApi):
    dataset_populator: DatasetPopulator
    framework_tool_and_types = True
    require_admin_user = False
    admin_user_email = "data-manager@galaxyproject.org"
    container_type = "docker"

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["check_migrate_databases"] = False
        config["admin_users"] = cls.admin_user_email

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.workflow_populator = WorkflowPopulator(self.galaxy_interactor)

    def test_run_data_manager_workflow(self):
        self.install_repository("devteam", "data_manager_fetch_genome_dbkeys_all_fasta", "4d3eff1bc421")
        self.install_repository("devteam", "data_manager_bwa_mem_index_builder", "9e993022c762")
        with self._different_user(email=self.admin_user_email), self.dataset_populator.test_history() as history_id:
            self.workflow_populator.run_workflow(
                """
class: GalaxyWorkflow
label: Indexing workflow
inputs:
  dbkey:
    optional: false
    type: string
  display name:
    optional: false
    type: string
  name:
    optional: false
    type: string
  id:
    optional: false
    type: string
  url:
    optional: false
    type: string
steps:
  fasta_index:
    tool_id: toolshed.g2.bx.psu.edu/repos/devteam/data_manager_fetch_genome_dbkeys_all_fasta/data_manager_fetch_genome_all_fasta_dbkey/0.0.4
    tool_version: 0.0.4
    tool_state:
      dbkey_source:
        dbkey_source_selector: new
      reference_source:
        reference_source_selector: url
      sorting:
        sort_selector: as_is
      __data_manager_mode: bundle
    in:
      dbkey_source|dbkey:
        source: dbkey
      dbkey_source|dbkey_name:
        source: display name
      reference_source|user_url:
        source: url
      sequence_id:
        source: id
      sequence_name:
        source: name

  bwa_mem_index:
    tool_id: toolshed.g2.bx.psu.edu/repos/devteam/data_manager_bwa_mem_index_builder/bwa_mem_index_builder_data_manager/0.0.5
    tool_version: 0.0.5
    tool_state:
      __data_manager_mode: bundle
    in:
      all_fasta_source: fasta_index/out_file

test_data:
    dbkey:
        value: wf_bundle
        type: raw
    display name:
        value: display name value
        type: raw
    id:
        value: wf_bundle_id
        type: raw
    name:
        value: workflow bundle
        type: raw
    url:
        value: https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test-data/1.fasta
        type: raw
""",
                history_id=history_id,
                wait=True,
                assert_ok=True,
            )
