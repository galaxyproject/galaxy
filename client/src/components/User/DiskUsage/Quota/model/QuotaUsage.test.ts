import { DEFAULT_QUOTA_SOURCE_LABEL, QuotaUsage, type QuotaUsageResponse } from "./QuotaUsage";

const RAW_DEFAULT_QUOTA_USAGE: QuotaUsageResponse = {
    quota_source_label: undefined,
    quota_bytes: 68468436,
    total_disk_usage: 4546654,
    quota_percent: 20,
};

const RAW_LIMITED_SOURCE_QUOTA_USAGE: QuotaUsageResponse = {
    quota_source_label: "The source",
    quota_bytes: 68468436,
    total_disk_usage: 4546654,
    quota_percent: 20,
};

const RAW_UNLIMITED_SOURCE_QUOTA_USAGE: QuotaUsageResponse = {
    quota_source_label: "The unlimited source",
    quota_bytes: undefined,
    total_disk_usage: 4546654,
    quota_percent: undefined,
};

describe("QuotaUsage", () => {
    const defaultQuotaUsage = new QuotaUsage(RAW_DEFAULT_QUOTA_USAGE);
    const limitedQuotaUsage = new QuotaUsage(RAW_LIMITED_SOURCE_QUOTA_USAGE);
    const unlimitedQuotaUsage = new QuotaUsage(RAW_UNLIMITED_SOURCE_QUOTA_USAGE);

    test("default quota source label should have the default value", () => {
        expect(defaultQuotaUsage.sourceLabel).toBe(DEFAULT_QUOTA_SOURCE_LABEL);
    });

    test("non default quota source label should have the correct value", () => {
        expect(limitedQuotaUsage.sourceLabel).toBe(RAW_LIMITED_SOURCE_QUOTA_USAGE.quota_source_label);
    });

    test("nice quota should be 'unlimited' when the source is unlimited", () => {
        expect(unlimitedQuotaUsage.isUnlimited).toBe(true);
        expect(unlimitedQuotaUsage.niceQuota).toBe("unlimited");
    });

    test("is unlimited should indicate the correct status", () => {
        expect(unlimitedQuotaUsage.isUnlimited).toBe(true);
        expect(limitedQuotaUsage.isUnlimited).toBe(false);
    });
});
