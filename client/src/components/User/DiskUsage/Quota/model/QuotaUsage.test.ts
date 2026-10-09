import { describe, expect, it } from "vitest";

import { DEFAULT_QUOTA_SOURCE_LABEL, toQuotaUsage, type UserQuotaUsageData } from "./QuotaUsage";

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
    it.each([
        { name: "the default source", data: RAW_DEFAULT_QUOTA_USAGE, expectedLabel: DEFAULT_QUOTA_SOURCE_LABEL },
        { name: "a named source", data: RAW_LIMITED_SOURCE_QUOTA_USAGE, expectedLabel: "The source" },
    ])("labels $name", ({ data, expectedLabel }) => {
        const quotaUsage = toQuotaUsage(data);
        expect(quotaUsage.sourceLabel).toBe(expectedLabel);
    });

    it("formats unlimited quota as 'unlimited'", () => {
        const quotaUsage = toQuotaUsage(RAW_UNLIMITED_SOURCE_QUOTA_USAGE);
        expect(quotaUsage.isUnlimited).toBe(true);
        expect(quotaUsage.niceQuota).toBe("unlimited");
    });

    it.each([
        { name: "an unlimited source", data: RAW_UNLIMITED_SOURCE_QUOTA_USAGE, expected: true },
        { name: "a limited source", data: RAW_LIMITED_SOURCE_QUOTA_USAGE, expected: false },
    ])("reports unlimited status for $name", ({ data, expected }) => {
        const quotaUsage = toQuotaUsage(data);
        expect(quotaUsage.isUnlimited).toBe(expected);
    });
});
