import { mount } from "@vue/test-utils";
import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import flushPromises from "flush-promises";
import { createPinia } from "pinia";
import { getLocalVue } from "tests/jest/helpers";

import { mockFetcher } from "@/api/schema/__mocks__";
import { getCurrentUser } from "@/stores/users/queries";
import { useUserStore } from "@/stores/userStore";

import { UserQuotaUsageData } from "./Quota/model";

import DiskUsageSummary from "./DiskUsageSummary.vue";

jest.mock("@/api/schema");
jest.mock("@/stores/users/queries");

const localVue = getLocalVue();

const quotaUsageClassSelector = ".quota-usage";
const basicDiskUsageSummaryId = "#basic-disk-usage-summary";

const fakeUserWithQuota = {
    id: "fakeUser",
    email: "fakeUserEmail",
    tags_used: [],
    isAnonymous: false,
    total_disk_usage: 1048576,
    quota_bytes: 104857600,
    quota_percent: 1,
    quota_source_label: "Default",
};

// TODO: Replace this with a mockFetcher when #16608 is merged
const mockGetCurrentUser = getCurrentUser as jest.Mock;
mockGetCurrentUser.mockImplementation(() => Promise.resolve(fakeUserWithQuota));

const fakeQuotaUsages: UserQuotaUsageData[] = [
    {
        quota_source_label: "Default",
        quota_bytes: 104857600,
        total_disk_usage: 1048576,
    },
];

const FAKE_TASK_ID = "fakeTaskId";

async function mountDiskUsageSummaryWrapper(enableQuotas: boolean) {
    mockFetcher
        .path("/api/configuration")
        .method("get")
        .mock({ data: { enable_quotas: enableQuotas } });
    mockFetcher.path("/api/users/{user_id}/usage").method("get").mock({ data: fakeQuotaUsages });
    mockFetcher
        .path("/api/users/current/recalculate_disk_usage")
        .method("put")
        .mock({ status: 200, data: { id: FAKE_TASK_ID } });

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
    let axiosMock: MockAdapter;

    beforeEach(async () => {
        axiosMock = new MockAdapter(axios);
    });

    afterEach(async () => {
        axiosMock.reset();
    });

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

    it("should display the correct quota usage", async () => {
        const enableQuotasInConfig = true;
        const wrapper = await mountDiskUsageSummaryWrapper(enableQuotasInConfig);
        const quotaUsage = wrapper.find(quotaUsageClassSelector);
        expect(quotaUsage.text()).toContain("1 MB");
    });

    it("should refresh the quota usage when the user clicks the refresh button", async () => {
        const enableQuotasInConfig = true;
        const wrapper = await mountDiskUsageSummaryWrapper(enableQuotasInConfig);
        const quotaUsage = wrapper.find(quotaUsageClassSelector);
        expect(quotaUsage.text()).toContain("1 MB");
        const updatedFakeQuotaUsages: UserQuotaUsageData[] = [
            {
                quota_source_label: "Default",
                quota_bytes: 104857600,
                total_disk_usage: 2097152,
            },
        ];
        mockFetcher.path("/api/users/{user_id}/usage").method("get").mock({ data: updatedFakeQuotaUsages });
        axiosMock.onGet(`/api/tasks/${FAKE_TASK_ID}/state`).reply(200, "SUCCESS");
        const refreshButton = wrapper.find("#refresh-disk-usage");
        await refreshButton.trigger("click");
        const refreshingAlert = wrapper.find(".refreshing-alert");
        expect(refreshingAlert.exists()).toBe(true);
        // Make sure the refresh has finished before checking the quota usage
        await flushPromises();
        // The refreshing alert should disappear and the quota usage should be updated
        expect(refreshingAlert.exists()).toBe(false);
        expect(quotaUsage.text()).toContain("2 MB");
    });
});
