import { mount } from "@vue/test-utils";
import { getLocalVue } from "jest/helpers";
import QuotaUsageBar from "./QuotaUsageBar";

const localVue = getLocalVue();

const NON_DEFAULT_QUOTA_USAGE = {
    sourceLabel: "The label",
    quotaInBytes: 68468436,
    totalDiskUsageInBytes: 4546654,
    quotaPercent: 20,
    niceQuota: "X MB",
    niceTotalDiskUsage: "Y MB",
    isUnlimited: false,
};

const UNLIMITED_USAGE = {
    sourceLabel: "Unlimited",
    quotaInBytes: null,
    totalDiskUsageInBytes: 4546654,
    quotaPercent: null,
    niceQuota: "unlimited",
    niceTotalDiskUsage: "Y MB",
    isUnlimited: true,
};

function mountQuotaUsageBarWith(quotaUsage) {
    const wrapper = mount(QuotaUsageBar, { propsData: { quotaUsage } }, localVue);
    return wrapper;
}

describe("QuotaUsageBar.vue", () => {
    it("should display the quota source label when the quota source is not the default one", async () => {
        const wrapper = mountQuotaUsageBarWith(NON_DEFAULT_QUOTA_USAGE);
        const storageSourceLabel = wrapper.find(".storage-source-label");
        expect(wrapper.vm.isDefaultQuota).toBe(false);
        expect(storageSourceLabel.exists()).toBe(true);
        expect(storageSourceLabel.text()).toBe(NON_DEFAULT_QUOTA_USAGE.sourceLabel);
    });

    it("should show the usage percent when there is a quota limit", async () => {
        const wrapper = mountQuotaUsageBarWith(NON_DEFAULT_QUOTA_USAGE);
        const percentText = wrapper.find(".quota-percent-text");
        expect(wrapper.vm.quotaHasLimit).toBe(true);
        expect(percentText.exists()).toBe(true);
        expect(percentText.text()).toContain(NON_DEFAULT_QUOTA_USAGE.quotaPercent.toString());
    });

    it("should not show percentage when there is no quota limit", async () => {
        const wrapper = mountQuotaUsageBarWith(UNLIMITED_USAGE);
        const percentText = wrapper.find(".quota-percent-text");
        expect(wrapper.vm.quotaHasLimit).toBe(false);
        expect(percentText.exists()).toBe(false);
    });
});
