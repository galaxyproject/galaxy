import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { expect, within } from "storybook/test";

import { toQuotaUsage } from "./model";

import QuotaUsageSummary from "./QuotaUsageSummary.vue";

const LARGE_BYTES = 654846535;
const SMALL_BYTES = 68468436;

/** A source using `usedBytes`, with a quota of `quotaBytes` and the percent the API reports for it, or unlimited without one. */
function quota(label: string, usedBytes: number, quotaBytes?: number) {
    return toQuotaUsage({
        quota_source_label: label,
        quota_bytes: quotaBytes,
        quota_percent: quotaBytes ? Math.min(Math.floor((usedBytes / quotaBytes) * 100), 100) : undefined,
        total_disk_usage: usedBytes,
    });
}

const meta = {
    title: "User/DiskUsage/Quota/QuotaUsageSummary",
    component: QuotaUsageSummary,
} satisfies Meta<typeof QuotaUsageSummary>;

export default meta;
type Story = StoryObj<typeof meta>;
type PlayContext = Parameters<NonNullable<Story["play"]>>[0];

function headingNames({ canvas }: PlayContext, level: number) {
    return canvas.getAllByRole("heading", { level }).map((heading) => heading.textContent?.replace(/\s+/g, " ").trim());
}

/** The summary heading's figure is bold. */
async function expectBoldInSummary({ canvas }: PlayContext, summary: string, bold: string) {
    const heading = canvas.getByRole("heading", { level: 2, name: summary });
    await expect(within(heading).getByText(bold).tagName).toBe("B");
}

/**
 * Two limited sources count their quotas, not their usage, toward the total; the unlimited source, though in use,
 * adds nothing.
 */
export const MixedQuotas: Story = {
    args: {
        quotaUsages: [
            quota("source 1", Math.round(LARGE_BYTES / 2), LARGE_BYTES),
            quota("source 2", SMALL_BYTES, SMALL_BYTES),
            quota("Unlimited source", SMALL_BYTES),
        ],
    },
    play: async (context) => {
        const { canvas, step } = context;
        await step("See the two limited sources' quotas summed, in bold, as the total disk quota", async () => {
            await expectBoldInSummary(context, "You've got 723.3 MB of total disk quota", "723.3 MB");
        });
        await step(
            "See the summary's note and a usage bar for each source, in order, with the percent only where there's a limit",
            async () => {
                await expect(headingNames(context, 2)).toEqual([
                    "You've got 723.3 MB of total disk quota",
                    "source 1 storage source",
                    "source 2 storage source",
                    "Unlimited source storage source",
                ]);
                await expect(headingNames(context, 3)).toEqual([
                    "This is the maximum disk space that you can use across all your storage sources. Unlimited storage sources are not taken into account",
                    "327.4 MB of 654.8 MB used",
                    "68.5 MB of 68.5 MB used",
                    "68.5 MB used",
                ]);
                await expect(
                    canvas.getAllByText(/% of disk quota used/).map((text) => text.textContent?.trim()),
                ).toEqual(["50% of disk quota used", "100% of disk quota used"]);
            },
        );
    },

    // TODO a11y: aria-progressbar-name (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

/** No source has a quota, so the summary reports unlimited disk space. */
export const AllUnlimited: Story = {
    args: {
        quotaUsages: [quota("Unlimited source 1", LARGE_BYTES), quota("Unlimited source 2", SMALL_BYTES)],
    },
    play: async (context) => {
        const { canvas, step } = context;
        await step("See the summary report unlimited disk quota, in bold", async () => {
            await expectBoldInSummary(context, "You've got unlimited disk quota", "unlimited");
        });
        await step("See the summary's note and a usage bar for each source, with no percent", async () => {
            await expect(headingNames(context, 2)).toEqual([
                "You've got unlimited disk quota",
                "Unlimited source 1 storage source",
                "Unlimited source 2 storage source",
            ]);
            await expect(headingNames(context, 3)).toEqual([
                "All your storage sources have unlimited disk space. Enjoy!",
                "654.8 MB used",
                "68.5 MB used",
            ]);
            await expect(canvas.queryByText(/% of disk quota used/)).not.toBeInTheDocument();
        });
    },

    // TODO a11y: aria-progressbar-name (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};
