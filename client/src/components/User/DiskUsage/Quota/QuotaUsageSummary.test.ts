import { getLocalVue } from "@tests/vitest/helpers";
import { enableAutoUnmount, shallowMount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";

import { type QuotaUsage, toQuotaUsage } from "./model";

import QuotaUsageBar from "./QuotaUsageBar.vue";
import QuotaUsageSummary from "./QuotaUsageSummary.vue";

enableAutoUnmount(afterEach);

const QUOTA_1_BYTES = 654846535;
const QUOTA_2_BYTES = 68468436;

const MIXED_QUOTAS: QuotaUsage[] = [
    toQuotaUsage({
        quota_source_label: "source 1",
        quota_bytes: QUOTA_1_BYTES,
        total_disk_usage: QUOTA_1_BYTES,
    }),
    toQuotaUsage({
        quota_source_label: "source 2",
        quota_bytes: QUOTA_2_BYTES,
        total_disk_usage: QUOTA_2_BYTES,
    }),
    toQuotaUsage({
        quota_source_label: "Unlimited source",
        quota_bytes: undefined,
        total_disk_usage: 0,
    }),
];

function mountQuotaUsageSummaryWith(quotaUsages: QuotaUsage[]) {
    return shallowMount(QuotaUsageSummary, { props: { quotaUsages }, global: getLocalVue(true) });
}

describe("QuotaUsageSummary", () => {
    it("sums finite quotas and excludes the unlimited source", () => {
        const wrapper = mountQuotaUsageSummaryWith(MIXED_QUOTAS);
        const expectedTotalBytes = QUOTA_1_BYTES + QUOTA_2_BYTES;
        expect(wrapper.vm.totalQuotaInBytes).toBe(expectedTotalBytes);
        expect(wrapper.get("h2 b").text()).toBe("723.3 MB");
        expect(wrapper.get("h2").text()).toContain("of total disk quota");
    });

    it("passes each finite or unlimited quota to its bar", () => {
        const wrapper = mountQuotaUsageSummaryWith(MIXED_QUOTAS);
        const expectedNumberOfBars = MIXED_QUOTAS.length;

        expect(wrapper.findAll(".quota-usage-bar")).toHaveLength(expectedNumberOfBars);
        expect(wrapper.findAllComponents(QuotaUsageBar).map((bar) => bar.props("quotaUsage"))).toEqual(MIXED_QUOTAS);
    });

    it("shows unlimited total quota when every source is unlimited", () => {
        const unlimitedQuotas: QuotaUsage[] = [
            toQuotaUsage({
                quota_source_label: "Unlimited source 1",
                quota_bytes: undefined,
                total_disk_usage: QUOTA_1_BYTES,
            }),
            toQuotaUsage({
                quota_source_label: "Unlimited source 2",
                quota_bytes: undefined,
                total_disk_usage: QUOTA_2_BYTES,
            }),
        ];
        const wrapper = mountQuotaUsageSummaryWith(unlimitedQuotas);
        const summaryText = wrapper.get("h2").text();
        expect(summaryText).toContain("unlimited");
    });
});
