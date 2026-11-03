import { getLocalVue } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";

import { type QuotaUsage, toQuotaUsage } from "./model";

import QuotaUsageBar from "./QuotaUsageBar.vue";

const localVue = getLocalVue();

enableAutoUnmount(afterEach);

const NON_DEFAULT_QUOTA_USAGE: QuotaUsage = toQuotaUsage({
    quota_source_label: "The label",
    quota_bytes: 68468436,
    total_disk_usage: 4546654,
    quota_percent: 20,
});

const UNLIMITED_USAGE: QuotaUsage = toQuotaUsage({
    quota_source_label: "Unlimited",
    quota_bytes: undefined,
    total_disk_usage: 4546654,
    quota_percent: undefined,
});

function mountQuotaUsageBarWith(quotaUsage: QuotaUsage) {
    return mount(QuotaUsageBar, { props: { quotaUsage }, global: localVue });
}

describe("QuotaUsageBar.vue", () => {
    it("names the usage bar for an unlimited storage source", () => {
        const wrapper = mountQuotaUsageBarWith(UNLIMITED_USAGE);
        expect(wrapper.get('[role="progressbar"]').attributes("aria-label")).toBe("Unlimited disk quota used");
    });

    it("names each progress bar by its storage source and retains its quota value", () => {
        const wrapper = mountQuotaUsageBarWith(NON_DEFAULT_QUOTA_USAGE);
        const progress = wrapper.get('[role="progressbar"]');

        expect(progress.attributes("aria-label")).toBe("The label disk quota used");
        expect(progress.attributes("aria-valuenow")).toBe("20");
        expect(progress.attributes("aria-valuemax")).toBe("100");
    });

    it("displays the source label for a non-default quota", () => {
        const wrapper = mountQuotaUsageBarWith(NON_DEFAULT_QUOTA_USAGE);
        const storageSourceLabel = wrapper.find(".storage-source-label");
        expect(wrapper.vm.isDefaultQuota).toBe(false);
        expect(storageSourceLabel.exists()).toBe(true);
        expect(storageSourceLabel.text()).toBe(NON_DEFAULT_QUOTA_USAGE.sourceLabel);
    });

    it("shows the usage percent when the quota has a limit", () => {
        const wrapper = mountQuotaUsageBarWith(NON_DEFAULT_QUOTA_USAGE);
        const percentText = wrapper.find(".quota-percent-text");
        expect(wrapper.vm.quotaHasLimit).toBe(true);
        expect(percentText.exists()).toBe(true);
        expect(percentText.text()).toContain(NON_DEFAULT_QUOTA_USAGE.quotaPercent?.toString());
    });

    it("hides the usage percent when the quota is unlimited", () => {
        const wrapper = mountQuotaUsageBarWith(UNLIMITED_USAGE);
        const percentText = wrapper.find(".quota-percent-text");
        expect(wrapper.vm.quotaHasLimit).toBe(false);
        expect(percentText.exists()).toBe(false);
    });
});
