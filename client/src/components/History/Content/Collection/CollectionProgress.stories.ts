import type { Meta, StoryObj } from "@storybook/vue3-vite";

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

export const Running: Story = { args: { summary: jobStateSummary({ all_jobs: 3, running: 3 }) } };

export const FailedOkAndRunning: Story = {
    args: { summary: jobStateSummary({ all_jobs: 5, running: 3, failed: 1, ok: 1 }) },
};

export const Queued: Story = { args: { summary: jobStateSummary({ all_jobs: 3, queued: 3 }) } };

/** Once every job has finished OK, the bar goes away. */
export const AllOk: Story = { args: { summary: jobStateSummary({ all_jobs: 2, ok: 2 }) } };
