import { shallowMount } from "@vue/test-utils";
import { getLocalVue } from "jest/helpers";
import QuotaUsageSummary from "./QuotaUsageSummary";

const localVue = getLocalVue();

const QUOTA_1_BYTES = 654846535;
const QUOTA_2_BYTES = 68468436;

const FAKE_QUOTA_USAGES_LIST = [
    {
        sourceLabel: "source 1",
        quotaInBytes: QUOTA_1_BYTES,
    },
    {
        sourceLabel: "source 2",
        quotaInBytes: QUOTA_2_BYTES,
    },
    {
        sourceLabel: "Unlimited source",
        quotaInBytes: null,
        isUnlimited: true,
    },
];

function mountQuotaUsageSummaryWith(quotaUsages) {
    const wrapper = shallowMount(QuotaUsageSummary, { propsData: { quotaUsages } }, localVue);
    return wrapper;
}

describe("QuotaUsageSummary.vue", () => {
    it("should calculate the total amount of quotas without the unlimited", () => {
        const wrapper = mountQuotaUsageSummaryWith(FAKE_QUOTA_USAGES_LIST);
        const expectedTotalBytes = QUOTA_1_BYTES + QUOTA_2_BYTES;

        expect(wrapper.vm.totalQuota).toBe(expectedTotalBytes);
    });

    it("should display a quota bar for each quota", () => {
        const wrapper = mountQuotaUsageSummaryWith(FAKE_QUOTA_USAGES_LIST);
        const expectedNumberOfBars = FAKE_QUOTA_USAGES_LIST.length;

        expect(wrapper.findAll("quotausagebar-stub").length).toBe(expectedNumberOfBars);
    });

    it("should display `unlimited` quota when all sources are unlimited", async () => {
        const FAKE_UNLIMITED_QUOTA_USAGES = [
            {
                sourceLabel: "Unlimited source 1",
                quotaInBytes: null,
                isUnlimited: true,
            },
            {
                sourceLabel: "Unlimited source 2",
                quotaInBytes: null,
                isUnlimited: true,
            },
        ];
        const wrapper = mountQuotaUsageSummaryWith(FAKE_UNLIMITED_QUOTA_USAGES);
        const summaryText = wrapper.find("h2").text();
        expect(summaryText).toContain("unlimited");
    });
});
