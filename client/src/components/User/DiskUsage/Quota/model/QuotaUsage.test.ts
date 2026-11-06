import { describe, expect, test } from "vitest";

import { toQuotaUsage, type UserQuotaUsageData } from "./QuotaUsage";

const RAW_DEFAULT_QUOTA_USAGE: UserQuotaUsageData = {
    quota_source_label: undefined,
    quota_bytes: 68468436,
    total_disk_usage: 4546654,
    quota_percent: 20,
};

const RAW_LIMITED_SOURCE_QUOTA_USAGE: UserQuotaUsageData = {
    quota_source_label: "The source",
    quota_bytes: 68468436,
    total_disk_usage: 4546654,
    quota_percent: 20,
};

const RAW_UNLIMITED_SOURCE_QUOTA_USAGE: UserQuotaUsageData = {
    quota_source_label: "The unlimited source",
    quota_bytes: undefined,
    total_disk_usage: 4546654,
    quota_percent: undefined,
};

describe("QuotaUsage", () => {
    const defaultQuotaUsage = toQuotaUsage(RAW_DEFAULT_QUOTA_USAGE);
    const limitedQuotaUsage = toQuotaUsage(RAW_LIMITED_SOURCE_QUOTA_USAGE);
    const unlimitedQuotaUsage = toQuotaUsage(RAW_UNLIMITED_SOURCE_QUOTA_USAGE);

    test("raw source label should be null for the default source", () => {
        expect(defaultQuotaUsage.rawSourceLabel).toBeNull();
        expect(limitedQuotaUsage.rawSourceLabel).toBe(RAW_LIMITED_SOURCE_QUOTA_USAGE.quota_source_label);
    });

    test("nice quota should be 'unlimited' when the source is unlimited", () => {
        expect(unlimitedQuotaUsage.isUnlimited).toBe(true);
        expect(unlimitedQuotaUsage.niceQuota).toBe("unlimited");
    });

    test("is unlimited should indicate the correct status", () => {
        expect(unlimitedQuotaUsage.isUnlimited).toBe(true);
        expect(limitedQuotaUsage.isUnlimited).toBe(false);
    });

    // As the server, which holds jobs only when the usage exceeds the quota and treats a quota of 0 as none
    test.each([
        { case: "at its quota", quota: 1000, usage: 1000, isOverQuota: false },
        { case: "over its quota", quota: 1000, usage: 1001, isOverQuota: true },
        { case: "with no quota", quota: undefined, usage: 1001, isOverQuota: false },
        { case: "with a quota of 0", quota: 0, usage: 1001, isOverQuota: false },
    ])("is over quota is $isOverQuota for a source $case", ({ quota, usage, isOverQuota }) => {
        const quotaUsage = toQuotaUsage({ quota_source_label: "a", quota_bytes: quota, total_disk_usage: usage });
        expect(quotaUsage.isOverQuota).toBe(isOverQuota);
    });
});
