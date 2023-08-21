import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia } from "pinia";
import { getLocalVue } from "tests/jest/helpers";

import MockCurrentUser from "@/components/providers/MockCurrentUser";
import MockProvider from "@/components/providers/MockProvider";
import { mockFetcher } from "@/schema/__mocks__";
import { useUserStore } from "@/stores/userStore";

import DiskUsageSummary from "./DiskUsageSummary.vue";

jest.mock("@/schema");

const localVue = getLocalVue();

const quotaUsageSummaryComponentId = "quota-usage-summary";
const basicDiskUsageSummaryId = "basic-disk-usage-summary";

const fakeUser = {
    total_disk_usage: 1054068,
};
const CurrentUserMock = MockCurrentUser(fakeUser);
const QuotaUsageProviderMock = MockProvider({
    result: [],
});
const QuotaUsageSummaryMock = { template: `<div id='${quotaUsageSummaryComponentId}'/>` };

async function mountDiskUsageSummaryWrapper(enableQuotas: boolean) {
    mockFetcher
        .path("/api/configuration")
        .method("get")
        .mock({ data: { enable_quotas: enableQuotas } });
    const pinia = createPinia();
    const wrapper = mount(DiskUsageSummary, {
        stubs: {
            CurrentUser: CurrentUserMock,
            QuotaUsageProvider: QuotaUsageProviderMock,
            QuotaUsageSummary: QuotaUsageSummaryMock,
        },
        localVue,
        pinia,
    });
    const userStore = useUserStore();
    userStore.currentUser = { id: "fakeUser", email: "fakeUserEmail", tags_used: [], isAnonymous: false };
    await flushPromises();
    return wrapper;
}

describe("DiskUsageSummary.vue", () => {
    it("should display basic disk usage summary if quotas are NOT enabled", async () => {
        const enableQuotasInConfig = false;
        const wrapper = await mountDiskUsageSummaryWrapper(enableQuotasInConfig);
        expect(wrapper.find(`#${basicDiskUsageSummaryId}`).exists()).toBe(true);
        expect(wrapper.find(`#${quotaUsageSummaryComponentId}`).exists()).toBe(false);
    });

    it("should display quota usage summary if quotas are enabled", async () => {
        const enableQuotasInConfig = true;
        const wrapper = await mountDiskUsageSummaryWrapper(enableQuotasInConfig);
        expect(wrapper.find(`#${basicDiskUsageSummaryId}`).exists()).toBe(false);
        expect(wrapper.find(`#${quotaUsageSummaryComponentId}`).exists()).toBe(true);
    });
});
