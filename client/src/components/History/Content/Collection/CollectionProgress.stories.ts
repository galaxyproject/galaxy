import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { expect, within } from "storybook/test";

import { jobStateSummary } from "./test_fixtures";

import CollectionProgress from "./CollectionProgress.vue";

/**
 * The bar under a collection in the history panel while the jobs making its elements run: failed jobs
 * red, finished green, running yellow and waiting grey.
 */
const meta = {
    title: "History/Content/Collection/CollectionProgress",
    component: CollectionProgress,
    // A JobStateSummary instance; the Controls panel would replace it with a plain object.
    argTypes: { summary: { control: false } },
} satisfies Meta<typeof CollectionProgress>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Running: Story = {
    args: { summary: jobStateSummary({ all_jobs: 3, running: 3 }) },
    play: async ({ canvasElement }) => {
        const bars = within(canvasElement).getAllByRole("progressbar");
        await expect(bars).toHaveLength(1);
        await expect(bars[0]).toHaveAttribute("aria-valuenow", "3");
    },
};

export const FailedOkAndRunning: Story = {
    args: { summary: jobStateSummary({ all_jobs: 5, running: 3, failed: 1, ok: 1 }) },
    play: async ({ canvasElement }) => {
        const bars = within(canvasElement).getAllByRole("progressbar");
        await expect(bars).toHaveLength(3);
        for (const [index, count] of ["1", "1", "3"].entries()) {
            await expect(bars[index]).toHaveAttribute("aria-valuenow", count);
        }
    },
};

export const Queued: Story = {
    args: { summary: jobStateSummary({ all_jobs: 3, queued: 3 }) },
    play: async ({ canvasElement }) => {
        const bars = within(canvasElement).getAllByRole("progressbar");
        await expect(bars).toHaveLength(1);
        await expect(bars[0]).toHaveAttribute("aria-valuenow", "3");
    },
};

/** Once every job has finished OK, the bar goes away. */
export const AllOk: Story = {
    args: { summary: jobStateSummary({ all_jobs: 2, ok: 2 }) },
    play: async ({ canvasElement }) => {
        // The summary is synchronous; the story is mounted before this play runs.
        await expect(within(canvasElement).queryAllByRole("progressbar")).toHaveLength(0);
    },
};
