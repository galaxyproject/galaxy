"""Integration tests for changing object stores."""

import string

from ._base import BaseObjectStoreIntegrationTestCase

DISTRIBUTED_OBJECT_STORE_CONFIG_TEMPLATE = string.Template(
    """<?xml version="1.0"?>
<object_store type="distributed" id="primary" order="0">
    <backends>
        <backend id="default" allow_selection="true" type="disk" weight="1" device="tmp_disk" name="Default Store 1">
            <files_dir path="${temp_directory}/files_default"/>
            <extra_dir type="temp" path="${temp_directory}/tmp_default"/>
            <extra_dir type="job_work" path="${temp_directory}/job_working_directory_default"/>
        </backend>
        <backend id="temp_short" allow_selection="true" type="disk" weight="0" device="tmp_disk" name="Temp - Short Term">
            <quota source="shorter_term" />
            <files_dir path="${temp_directory}/files_temp"/>
            <extra_dir type="temp" path="${temp_directory}/tmp_temp"/>
            <extra_dir type="job_work" path="${temp_directory}/job_working_directory_temp"/>
        </backend>
        <backend id="temp_long" allow_selection="true" type="disk" weight="0" device="tmp_disk" name="Temp - Longer Term">
            <quota source="longer_term" />
            <files_dir path="${temp_directory}/files_temp"/>
            <extra_dir type="temp" path="${temp_directory}/tmp_temp"/>
            <extra_dir type="job_work" path="${temp_directory}/job_working_directory_temp"/>
        </backend>
    </backends>
</object_store>
"""
)

TEST_INPUT_FILES_CONTENT = "1 2 3"


class TestChangingStoreObjectStoreIntegration(BaseObjectStoreIntegrationTestCase):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        config["new_user_dataset_access_role_default_private"] = True
        cls._configure_object_store(DISTRIBUTED_OBJECT_STORE_CONFIG_TEMPLATE, config)
        config["enable_quotas"] = True

    def test_valid_in_device_swap(self):
        with self.dataset_populator.test_history() as history_id:
            hda = self.dataset_populator.new_dataset(history_id, content=TEST_INPUT_FILES_CONTENT, wait=True)

            payload = {
                "name": "quota_longer",
                "description": "quota_longer desc",
                "amount": "10 MB",
                "operation": "=",
                "default": "registered",
                "quota_source_label": "longer_term",
            }
            self.dataset_populator.create_quota(payload)

            payload = {
                "name": "quota_shorter",
                "description": "quota_shorter desc",
                "amount": "20 MB",
                "operation": "=",
                "default": "registered",
                "quota_source_label": "shorter_term",
            }
            self.dataset_populator.create_quota(payload)

            quotas = self.dataset_populator.get_quotas()
            assert len(quotas) == 2

            usage = self.dataset_populator.get_usage_for("longer_term")
            assert usage["total_disk_usage"] == 0
            usage = self.dataset_populator.get_usage_for("shorter_term")
            assert usage["total_disk_usage"] == 0
            usage = self.dataset_populator.get_usage_for(None)
            assert int(usage["total_disk_usage"]) == 6

            def count_in_object_store(object_store_id: str):
                return len(
                    self.dataset_populator.get_history_contents(
                        history_id, {"q": "object_store_id-eq", "qv": object_store_id, "v": "dev"}
                    )
                )

            def count_in_quota_source(quota_source_label: str):
                return len(
                    self.dataset_populator.get_history_contents(
                        history_id, {"q": "quota_source_label-eq", "qv": quota_source_label, "v": "dev"}
                    )
                )

            self.dataset_populator.get_history_contents(history_id, {"q": "state-eq", "qv": "ok", "v": "dev"})
            assert count_in_object_store("temp_short") == 0
            assert count_in_quota_source("shorter_term") == 0

            self.dataset_populator.update_object_store_id(hda["id"], "temp_short")
            usage = self.dataset_populator.get_usage_for("shorter_term")
            assert int(usage["total_disk_usage"]) == 6
            usage = self.dataset_populator.get_usage_for(None)
            assert int(usage["total_disk_usage"]) == 0

            assert count_in_object_store("temp_short") == 1
            assert count_in_quota_source("shorter_term") == 1

            self.dataset_populator.update_object_store_id(hda["id"], "temp_long")
            usage = self.dataset_populator.get_usage_for("shorter_term")
            assert int(usage["total_disk_usage"]) == 0
            usage = self.dataset_populator.get_usage_for("longer_term")
            assert int(usage["total_disk_usage"]) == 6
            usage = self.dataset_populator.get_usage_for(None)
            assert int(usage["total_disk_usage"]) == 0

            self.dataset_populator.update_object_store_id(hda["id"], "temp_short")
            usage = self.dataset_populator.get_usage_for("shorter_term")
            assert int(usage["total_disk_usage"]) == 6
            usage = self.dataset_populator.get_usage_for("longer_term")
            assert int(usage["total_disk_usage"]) == 0
            usage = self.dataset_populator.get_usage_for(None)
            assert int(usage["total_disk_usage"]) == 0
