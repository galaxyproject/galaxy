import string
from typing import TYPE_CHECKING

from galaxy_test.driver.integration_util import ConfiguresObjectStores
from galaxy_test.selenium.framework import managed_history
from .framework import (
    selenium_test,
    SeleniumIntegrationTestCase,
)

if TYPE_CHECKING:
    from galaxy_test.selenium.framework import SeleniumSessionDatasetPopulator


MSI_EXAMPLE_OBJECT_STORE_CONFIG_TEMPLATE = string.Template(
    """
<object_store type="distributed">
    <backends>
        <backend id="high_performance" allow_selection="true" type="disk" weight="1" name="High Performance Storage">
            <description>All MSI researchers have access to a high-performance, high capacity primary storage platform. This system currently provides 3.5 PB (petabytes) of storage. The integrity of the data is protected by daily snapshots and tape backups. It has sustained read and write speeds of up to 25 GB/sec.

There is default access to this storage by any MSI group with an active account. Very large needs can be also met, but need to be approved by the MSI HPC Allocation Committee. More details are available on the [Storage Allocations](https://www.msi.umn.edu/content/storage-allocations) page.

More information about MSI Storage can be found [here](https://www.msi.umn.edu/content/data-storage).
</description>
            <files_dir path="${temp_directory}/default"/>
            <badges>
                <faster />
                <more_stable />
                <backed_up>Backed up to MSI's long term tape drive nightly. More information about our tape drive can be found on our [Archive Tier Storage](https://www.msi.umn.edu/content/archive-tier-storage) page.</backed_up>
            </badges>
        </backend>
        <backend id="second" allow_selection="true" type="disk" weight="0" name="Second Tier Storage">
            <quota source="second_tier" />
            <description>MSI first added a Ceph object storage system in November 2014 as a second tier storage option. The system currently has around 10 PB of usable storage installed.

MSI's second tier storage is designed to address the growing need for resources that support data-intensive research. It is tightly integrated with other MSI storage and computing resources in order to support a wide variety of research data life cycles and data analysis workflows. In addition, this object storage platform offers new access modes, such as Amazon’s S3 (Simple Storage Service) interface, so that researchers can better manage their data and more seamlessly share data with other researchers whether or not the other researcher has an MSI account or is at the University of Minnesota.

More information about MSI Storage can be found [here](https://www.msi.umn.edu/content/data-storage).
</description>
            <files_dir path="${temp_directory}/temp"/>
            <badges>
                <faster />
                <less_stable />
                <not_backed_up />
                <less_secure>MSI's enterprise level data security policies and montioring have not yet been integrated with Ceph storage.</less_secure>
                <short_term>The data stored here is purged after a month.</short_term>
            </badges>
        </backend>
        <backend id="experimental" allow_selection="true" type="disk" weight="0" name="Experimental Scratch" private="true">
            <quota enabled="false" />
            <description>MSI Ceph storage that is purged more aggressively (weekly instead of monthly) and so it only appropriate for short term methods development and such. The rapid deletion of stored data enables us to provide this storage without a quota.

More information about MSI Storage can be found [here](https://www.msi.umn.edu/content/data-storage).
            </description>
            <files_dir path="${temp_directory}/temp"/>
            <badges>
                <faster />
                <less_stable />
                <not_backed_up />
                <less_secure>MSI's enterprise level data security policies and montioring have not yet been integrated with Ceph storage.</less_secure>
                <short_term>The data stored here is purged after a week.</short_term>
            </badges>
        </backend>
        <backend id="surfs" allow_selection="true" type="disk" weight="0" name="SURFS" private="true">
            <quota source="umn_surfs" />
            <description>Much of the data analysis conducted on MSI’s high-performance computing resources uses data gathered from UMN shared research facilities (SRFs). In recognition of the need for short to medium term storage for this data, MSI provides a service, Shared User Research Facilities Storage (SURFS), enabling SRFs to deliver data directly to MSI users. By providing a designated location for this data, MSI can focus data backup and other processes to these key datasets.  As part of this service, MSI will provide the storage of the data for one year from its delivery date.

It's expected that the consumers of these data sets will be responsible for discerning which data they may wish to keep past the 1-year term, and finding an appropriate place to keep it. There are several possible storage options both at MSI and the wider university. You can explore your options using OIT’s digital [storage options chooser tool](https://it.umn.edu/services-technologies/comparisons/select-digital-storage-options).

More information about MSI Storage can be found [here](https://www.msi.umn.edu/content/data-storage).</description>
            <badges>
                <slower />
                <more_secure>University of Minnesota data security analysist's have authorized this storage for the storage of human data.</more_secure>
                <more_stable />
                <backed_up />
            </badges>
        </backend>
    </backends>
</object_store>
"""
)


class TestObjectStoreSelectionSeleniumIntegration(SeleniumIntegrationTestCase, ConfiguresObjectStores):
    ensure_registered = True
    dataset_populator: "SeleniumSessionDatasetPopulator"

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        cls._configure_object_store(MSI_EXAMPLE_OBJECT_STORE_CONFIG_TEMPLATE, config)

    @selenium_test
    @managed_history
    def test_0_tools_to_default(self):
        self.run_environment_test_tool()
        self.wait_for_hid_ok_and_open_details(1)
        details = self.components.object_store_details
        text = details.stored_by_name.wait_for_text()
        assert "High Performance Storage" in text
        details.badge_of_type(type="faster").wait_for_present()
        details.badge_of_type(type="more_stable").wait_for_present()

    @selenium_test
    @managed_history
    def test_1_tools_override_run(self):
        self.run_environment_test_tool(select_storage="second")
        self.wait_for_hid_ok_and_open_details(1)
        details = self.components.object_store_details
        text = details.stored_by_name.wait_for_text()
        assert "Second Tier Storage" in text
        details.badge_of_type(type="less_stable").wait_for_present()

    @selenium_test
    @managed_history
    def test_2_user_override(self):
        self.navigate_to_user_preferences()
        preferences = self.components.preferences
        preferences.preferred_storage.wait_for_and_click()
        self.select_storage("second")
        self.run_environment_test_tool()
        self.wait_for_hid_ok_and_open_details(1)
        details = self.components.object_store_details
        text = details.stored_by_name.wait_for_text()
        assert "Second Tier Storage" in text
        details.badge_of_type(type="less_stable").wait_for_present()

    @selenium_test
    @managed_history
    def test_3_user_un_override(self):
        # doesn't actually test that it is reverted from the previous
        # test because each of these tests creates a new user - does
        # test the behavior of selecting default option in user preferences
        # though.
        self.navigate_to_user_preferences()
        preferences = self.components.preferences
        preferences.preferred_storage.wait_for_and_click()
        self.select_storage("__null__")
        self.run_environment_test_tool()
        self.wait_for_hid_ok_and_open_details(1)
        details = self.components.object_store_details
        text = details.stored_by_name.wait_for_text()
        assert "High Performance Storage" in text
        details.badge_of_type(type="faster").wait_for_present()
        details.badge_of_type(type="more_stable").wait_for_present()


class TestMultipleQuotasSeleniumIntegration(SeleniumIntegrationTestCase, ConfiguresObjectStores):
    dataset_populator: "SeleniumSessionDatasetPopulator"
    run_as_admin = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        cls._configure_object_store(MSI_EXAMPLE_OBJECT_STORE_CONFIG_TEMPLATE, config)
        config["enable_quotas"] = True

    @selenium_test
    def test_multiple_quota_sources_for_user(self):
        expected_bytes = 17

        # create a user to create a quota for...
        user_email = self._get_random_email("quota_user")
        self.register(user_email)
        self.logout()

        # give them a quota on second_tier of 10 times the
        # size of the output of the test tool.

        self.admin_login()
        quota_name = self._get_random_name(prefix="secondquota")
        self.create_quota(
            name=quota_name,
            amount=f"{expected_bytes * 10} B",
            quota_source_label="second_tier",
            user=user_email,
        )
        admin_component = self.components.admin
        quota_component = admin_component.quota
        quota_component.items.wait_for_element_count_of_at_least(1)
        self.logout()

        # run the tool twice - once in the default object store without
        # quota configured and once in second_tier storage with a quota
        # configured.
        self.submit_login(user_email)
        self.run_environment_test_tool()
        self.sleep_for(self.wait_types.UX_TRANSITION)
        self.run_environment_test_tool(select_storage="second")

        # Assert no quota information on an object store without
        # quota configured and check the usage and percent on the
        # the dataset stored in an object store with a configured
        # quota.

        details = self.components.object_store_details
        self.wait_for_hid_ok_and_open_details(1)
        details.usage_percent.assert_absent()

        self.wait_for_hid_ok_and_open_details(2)

        usage_summary_el = details.usage_details.wait_for_visible()
        assert usage_summary_el.get_attribute("quota-source-label") == "second_tier"

        bytes_el = details.usage_bytes.wait_for_visible()
        assert bytes_el.get_attribute("data-quota-usage") == f"{expected_bytes}"

        percent_el = details.usage_percent.wait_for_visible()
        assert percent_el.get_attribute("data-quota-percent") == "10"
