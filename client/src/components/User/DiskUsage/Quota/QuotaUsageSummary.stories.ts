import type { Meta, StoryObj } from "@storybook/vue3-vite";

import { toQuotaUsage } from "./model";

import QuotaUsageSummary from "./QuotaUsageSummary.vue";

const LARGE_BYTES = 654846535;
const SMALL_BYTES = 68468436;

/** A source using `usedBytes`, with a quota of `quotaBytes`, or unlimited without one. */
function quota(label: string, usedBytes: number, quotaBytes?: number) {
    return toQuotaUsage({ quota_source_label: label, quota_bytes: quotaBytes, total_disk_usage: usedBytes });
}

const meta = {
    title: "User/DiskUsage/Quota/QuotaUsageSummary",
    component: QuotaUsageSummary,
} satisfies Meta<typeof QuotaUsageSummary>;

export default meta;
type Story = StoryObj<typeof meta>;

/** Two sources at 100% of their quota count toward the total; the unlimited source doesn't. */
export const MixedQuotas: Story = {
    args: {
        quotaUsages: [
            quota("source 1", LARGE_BYTES, LARGE_BYTES),
            quota("source 2", SMALL_BYTES, SMALL_BYTES),
            quota("Unlimited source", 0),
        ],
    },
};

/** No source has a quota, so the summary reports unlimited disk space. */
export const AllUnlimited: Story = {
    args: {
        quotaUsages: [quota("Unlimited source 1", LARGE_BYTES), quota("Unlimited source 2", SMALL_BYTES)],
    },
};
