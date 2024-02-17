from ._base import BaseObjectStoreIntegrationTestCase
from .test_selection_with_resource_parameters import (
    DISTRIBUTED_OBJECT_STORE_CONFIG_TEMPLATE,
    JOB_CONFIG_FILE,
    JOB_RESOURCE_PARAMETERS_CONFIG_FILE,
)


class TestQuotaIntegration(BaseObjectStoreIntegrationTestCase):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        cls._configure_object_store(DISTRIBUTED_OBJECT_STORE_CONFIG_TEMPLATE, config)
        config["job_config_file"] = JOB_CONFIG_FILE
        config["job_resource_params_file"] = JOB_RESOURCE_PARAMETERS_CONFIG_FILE
        config["enable_quotas"] = True

    def test_selection_limit(self):
        with self.dataset_populator.test_history() as history_id:
            hda1 = self.dataset_populator.new_dataset(history_id, content="1 2 3\n4 5 6\n7 8 9\n")
            self.dataset_populator.wait_for_history(history_id)
            hda1_input = {"src": "hda", "id": hda1["id"]}

            quotas = self.dataset_populator.get_quotas()
            assert len(quotas) == 0

            payload = {
                "name": "defaultquota1",
                "description": "first default quota",
                "amount": "1 bytes",
                "operation": "=",
                "default": "registered",
            }
            self.dataset_populator.create_quota(payload)

            payload = {
                "name": "ebsquota1",
                "description": "first ebs quota",
                "amount": "100 MB",
                "operation": "=",
                "default": "registered",
                "quota_source_label": "ebs",
            }
            self.dataset_populator.create_quota(payload)

            quotas = self.dataset_populator.get_quotas()
            assert len(quotas) == 2

            hda2 = self.dataset_populator.new_dataset(history_id, content="1 2 3\n4 5 6\n7 8 9\n")
            self.dataset_populator.wait_for_history(history_id)

            hda2_now = self.dataset_populator.get_history_dataset_details(history_id, dataset=hda2, wait=False)
            assert hda2_now["state"] == "paused"

            create_10_inputs = {
                "input1": hda1_input,
                "input2": hda1_input,
                "__job_resource|__job_resource__select": "yes",
                "__job_resource|how_store": "slow",
            }
            create10_response = self.dataset_populator.run_tool(
                "create_10",
                create_10_inputs,
                history_id,
                assert_ok=False,
            )
            job_id = create10_response["jobs"][0]["id"]
            self.dataset_populator.wait_for_job(job_id)
            job_details = self.dataset_populator.get_job_details(job_id).json()
            # This job isn't paused, it goes through because we used a different
            # objectstore using job parameters.
            assert job_details["state"] == "ok"
