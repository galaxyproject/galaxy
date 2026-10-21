import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { expect, waitFor } from "storybook/test";

import BarChart from "./BarChart.vue";

const meta = {
    title: "User/DiskUsage/Visualizations/Charts/BarChart",
    component: BarChart,
    args: {
        title: "Datasets by history",
        description: "Compare the number of datasets stored in each history.",
        data: [
            { id: "rna-seq-history", label: "RNA-seq analysis", value: 24 },
            { id: "quality-control-history", label: "Quality control", value: 8 },
        ],
    },
} satisfies Meta<typeof BarChart>;

export default meta;
type Story = StoryObj<typeof meta>;
type PlayContext = Parameters<NonNullable<Story["play"]>>[0];

async function readLegend(context: PlayContext, labels: [string, string]) {
    const first = await context.canvas.findByText(labels[0], { exact: true }, { timeout: 5000 });
    // Legend entries have no list role; read their shared container from a known visible label.
    const entries = Array.from(first.parentElement!.parentElement!.children);
    await expect(entries).toHaveLength(2);
    for (const [index, entry] of entries.entries()) {
        await expect(entry).toBeVisible();
        await expect(entry.textContent?.trim()).toBe(labels[index]);
    }
}

async function readEmptyChart({ canvas, step }: PlayContext) {
    await step("Read the chart heading and its empty-state message", async () => {
        await expect(canvas.getByRole("heading", { name: "Datasets by history", level: 4 })).toBeVisible();
        await expect(
            canvas.getByText("No data to display. Populate some data and come back.", { exact: true }),
        ).toBeVisible();
    });
}

/** Dataset counts with a read-only legend. */
export const DatasetCounts: Story = {
    play: async (context) => {
        await context.step("Read dataset counts for both histories", async () => {
            await expect(context.canvas.getByRole("heading", { name: "Datasets by history", level: 4 })).toBeVisible();
            await expect(
                context.canvas.getByText("Compare the number of datasets stored in each history.", { exact: true }),
            ).toBeVisible();
            await readLegend(context, ["RNA-seq analysis: 24", "Quality control: 8"]);
        });
    },
};

/** Select a bar or legend entry to inspect one history's contribution. */
export const SelectableHistories: Story = { args: { enableSelection: true } };

/** No histories have contributed data yet. */
export const NoHistories: Story = { args: { data: [] }, play: readEmptyChart };

/** Histories exist, but each has zero datasets. */
export const EmptyHistories: Story = {
    play: readEmptyChart,
    args: {
        data: [
            { id: "rna-seq-history", label: "RNA-seq analysis", value: 0 },
            { id: "quality-control-history", label: "Quality control", value: 0 },
        ],
    },
};

/** Exact original records preserve the title, description and ordered legend checks. */
export const OriginalDatasetCounts: Story = {
    args: {
        title: "Test Bar Chart",
        description: "Test description",
        data: [
            { id: "id1", label: "foo", value: 1 },
            { id: "id2", label: "bar", value: 2 },
        ],
    },
    play: async (context) => {
        await context.step("Read the original title, description and both ordered legend entries", async () => {
            await expect(context.canvas.getByRole("heading", { name: "Test Bar Chart", level: 4 })).toBeVisible();
            await expect(context.canvas.getByText("Test description", { exact: true })).toBeVisible();
            await readLegend(context, ["foo: 1", "bar: 2"]);
        });
    },
};

/** Select one history through its legend and clear that selection again. */
export const SelectsHistoryFromLegend: Story = {
    args: { enableSelection: true },
    play: async (context) => {
        await context.step("Read the loaded legend before selecting a history", async () => {
            await readLegend(context, ["RNA-seq analysis: 24", "Quality control: 8"]);
            await expect(context.canvas.queryByText(/^Selected:/)).not.toBeInTheDocument();
        });
        await context.step("Select the RNA-seq history from its legend entry", async () => {
            await context.userEvent.click(context.canvas.getByText("RNA-seq analysis: 24", { exact: true }));
            await waitFor(
                () => expect(context.canvas.getByText("Selected: RNA-seq analysis", { exact: true })).toBeVisible(),
                { timeout: 5000 },
            );
        });
        await context.step("Clear the selected history by clicking its entry again", async () => {
            await context.userEvent.click(context.canvas.getByText("RNA-seq analysis: 24", { exact: true }));
            await waitFor(() => expect(context.canvas.queryByText(/^Selected:/)).not.toBeInTheDocument());
        });
    },
};
