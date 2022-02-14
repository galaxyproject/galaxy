import { mount } from "@vue/test-utils";
import MockConfigProvider from "components/providers/MockConfigProvider";
import MockCurrentUser from "components/providers/MockCurrentUser";
import MockProvider from "components/providers/MockProvider";
import flushPromises from "flush-promises";
import { getLocalVue } from "jest/helpers";
import DiskUsageSummary from "./DiskUsageSummary";

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

async function mountDiskUsageSummaryWrapper(enableQuotas) {
    const wrapper = mount(DiskUsageSummary, {
        stubs: {
            ConfigProvider: MockConfigProvider({
                enable_quotas: enableQuotas,
            }),
            CurrentUser: CurrentUserMock,
            QuotaUsageProvider: QuotaUsageProviderMock,
            QuotaUsageSummary: QuotaUsageSummaryMock,
        },
        localVue,
    });
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
