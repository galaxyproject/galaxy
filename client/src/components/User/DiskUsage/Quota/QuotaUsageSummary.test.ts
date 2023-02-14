import { shallowMount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import { QuotaUsage } from "./model";
import QuotaUsageSummary from "./QuotaUsageSummary.vue";

const localVue = getLocalVue();

const QUOTA_1_BYTES = 654846535;
const QUOTA_2_BYTES = 68468436;

const FAKE_QUOTA_USAGES_LIST: QuotaUsage[] = [
    new QuotaUsage({
        quota_source_label: "source 1",
        quota_bytes: QUOTA_1_BYTES,
        total_disk_usage: QUOTA_1_BYTES,
    }),
    new QuotaUsage({
        quota_source_label: "source 2",
        quota_bytes: QUOTA_2_BYTES,
        total_disk_usage: QUOTA_2_BYTES,
    }),
    new QuotaUsage({
        quota_source_label: "Unlimited source",
        quota_bytes: undefined,
        total_disk_usage: 0,
    }),
];

function mountQuotaUsageSummaryWith(quotaUsages: QuotaUsage[]) {
    const wrapper = shallowMount(QuotaUsageSummary, { propsData: { quotaUsages }, localVue });
    return wrapper;
}

describe("QuotaUsageSummary.vue", () => {
    it("should calculate the total amount of quotas without the unlimited", () => {
        const wrapper = mountQuotaUsageSummaryWith(FAKE_QUOTA_USAGES_LIST);
        const expectedTotalBytes = QUOTA_1_BYTES + QUOTA_2_BYTES;
        // TODO: explicit any because the type of the vm is not correctly inferred, remove when fixed
        expect((wrapper.vm as any).totalQuotaInBytes).toBe(expectedTotalBytes);
    });

    it("should display a quota bar for each quota", () => {
        const wrapper = mountQuotaUsageSummaryWith(FAKE_QUOTA_USAGES_LIST);
        const expectedNumberOfBars = FAKE_QUOTA_USAGES_LIST.length;

        expect(wrapper.findAll(".quota-usage-bar").length).toBe(expectedNumberOfBars);
    });

    it("should display `unlimited` quota when all sources are unlimited", async () => {
        const FAKE_UNLIMITED_QUOTA_USAGES: QuotaUsage[] = [
            new QuotaUsage({
                quota_source_label: "Unlimited source 1",
                quota_bytes: undefined,
                total_disk_usage: QUOTA_1_BYTES,
            }),
            new QuotaUsage({
                quota_source_label: "Unlimited source 2",
                quota_bytes: undefined,
                total_disk_usage: QUOTA_2_BYTES,
            }),
        ];
        const wrapper = mountQuotaUsageSummaryWith(FAKE_UNLIMITED_QUOTA_USAGES);
        const summaryText = wrapper.find("h2").text();
        expect(summaryText).toContain("unlimited");
    });
});
