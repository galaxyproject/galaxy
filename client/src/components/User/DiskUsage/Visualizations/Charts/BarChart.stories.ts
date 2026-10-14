import type { Meta, StoryObj } from "@storybook/vue3-vite";

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

/** Dataset counts with a read-only legend. */
export const DatasetCounts: Story = {};

/** Select a bar or legend entry to inspect one history's contribution. */
export const SelectableHistories: Story = { args: { enableSelection: true } };

/** No histories have contributed data yet. */
export const NoHistories: Story = { args: { data: [] } };

/** Histories exist, but each has zero datasets. */
export const EmptyHistories: Story = {
    args: {
        data: [
            { id: "rna-seq-history", label: "RNA-seq analysis", value: 0 },
            { id: "quality-control-history", label: "Quality control", value: 0 },
        ],
    },
};
