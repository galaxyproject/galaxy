import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import { QuotaUsage } from "./model";
import QuotaUsageBar from "./QuotaUsageBar.vue";

const localVue = getLocalVue();

const NON_DEFAULT_QUOTA_USAGE: QuotaUsage = new QuotaUsage({
    quota_source_label: "The label",
    quota_bytes: 68468436,
    total_disk_usage: 4546654,
    quota_percent: 20,
});

const UNLIMITED_USAGE: QuotaUsage = new QuotaUsage({
    quota_source_label: "Unlimited",
    quota_bytes: undefined,
    total_disk_usage: 4546654,
    quota_percent: undefined,
});

function mountQuotaUsageBarWith(quotaUsage: QuotaUsage) {
    const wrapper = mount(QuotaUsageBar, { propsData: { quotaUsage }, localVue });
    return wrapper;
}

describe("QuotaUsageBar.vue", () => {
    it("should display the quota source label when the quota source is not the default one", async () => {
        const wrapper = mountQuotaUsageBarWith(NON_DEFAULT_QUOTA_USAGE);
        const storageSourceLabel = wrapper.find(".storage-source-label");
        // TODO: explicit any because the type of the vm is not correctly inferred, remove when fixed
        expect((wrapper.vm as any).isDefaultQuota).toBe(false);
        expect(storageSourceLabel.exists()).toBe(true);
        expect(storageSourceLabel.text()).toBe(NON_DEFAULT_QUOTA_USAGE.sourceLabel);
    });

    it("should show the usage percent when there is a quota limit", async () => {
        const wrapper = mountQuotaUsageBarWith(NON_DEFAULT_QUOTA_USAGE);
        const percentText = wrapper.find(".quota-percent-text");
        // TODO: explicit any because the type of the vm is not correctly inferred, remove when fixed
        expect((wrapper.vm as any).quotaHasLimit).toBe(true);
        expect(percentText.exists()).toBe(true);
        expect(percentText.text()).toContain(NON_DEFAULT_QUOTA_USAGE.quotaPercent?.toString());
    });

    it("should not show percentage when there is no quota limit", async () => {
        const wrapper = mountQuotaUsageBarWith(UNLIMITED_USAGE);
        const percentText = wrapper.find(".quota-percent-text");
        // TODO: explicit any because the type of the vm is not correctly inferred, remove when fixed
        expect((wrapper.vm as any).quotaHasLimit).toBe(false);
        expect(percentText.exists()).toBe(false);
    });
});
