import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia } from "pinia";
import { getLocalVue } from "tests/jest/helpers";

import { mockFetcher } from "@/schema/__mocks__";
import { useUserStore } from "@/stores/userStore";

import DiskUsageSummary from "./DiskUsageSummary.vue";

jest.mock("@/schema");

const localVue = getLocalVue();

const quotaUsageClassSelector = ".quota-usage";
const basicDiskUsageSummaryId = "#basic-disk-usage-summary";

const fakeUserWithQuota = {
    id: "fakeUser",
    email: "fakeUserEmail",
    tags_used: [],
    isAnonymous: false,
    total_disk_usage: 1054068,
    quota_bytes: 1000000000,
    quota_percent: 0.1,
    quota_source_label: "Default",
};

async function mountDiskUsageSummaryWrapper(enableQuotas: boolean) {
    mockFetcher
        .path("/api/configuration")
        .method("get")
        .mock({ data: { enable_quotas: enableQuotas } });
    const pinia = createPinia();
    const wrapper = mount(DiskUsageSummary, {
        localVue,
        pinia,
    });
    const userStore = useUserStore();
    userStore.currentUser = fakeUserWithQuota;
    await flushPromises();
    return wrapper;
}

describe("DiskUsageSummary.vue", () => {
    it("should display basic disk usage summary if quotas are NOT enabled", async () => {
        const enableQuotasInConfig = false;
        const wrapper = await mountDiskUsageSummaryWrapper(enableQuotasInConfig);
        expect(wrapper.find(basicDiskUsageSummaryId).exists()).toBe(true);
        const quotaUsages = wrapper.findAll(quotaUsageClassSelector);
        expect(quotaUsages.length).toBe(0);
    });

    it("should display quota usage summary if quotas are enabled", async () => {
        const enableQuotasInConfig = true;
        const wrapper = await mountDiskUsageSummaryWrapper(enableQuotasInConfig);
        expect(wrapper.find(basicDiskUsageSummaryId).exists()).toBe(false);
        const quotaUsages = wrapper.findAll(quotaUsageClassSelector);
        expect(quotaUsages.length).toBe(1);
    });
});
