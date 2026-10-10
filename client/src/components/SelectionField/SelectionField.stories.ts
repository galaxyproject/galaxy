import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { withCurrentHistory } from "@tests/test-data/currentHistory";

import type { HDASummary } from "@/api";
import { http } from "@/api/client/__mocks__/http";

import { CURRENT_HISTORY, HISTORY_DATASETS } from "./test_fixtures";
import type { OptionType } from "./types";

import SelectionField from "./SelectionField.vue";

/** Answers the dataset search with the `datasets` whose name contains the search text, as Galaxy does. */
function currentHistoryDatasets(datasets: readonly HDASummary[]) {
    return http.get("/api/datasets", ({ query, response }) => {
        const text = (query.get("qv") ?? "").toLowerCase();
        return response(200).json(datasets.filter((dataset) => dataset.name?.toLowerCase().includes(text)));
    });
}

/** Picks what a Galaxy markdown directive or a visualization shows, here a dataset from the current history. */
const meta = {
    title: "SelectionField",
    component: SelectionField,
    decorators: [withCurrentHistory(CURRENT_HISTORY)],
    args: { objectType: "history_dataset_id" },
    parameters: { msw: { handlers: { datasets: currentHistoryDatasets(HISTORY_DATASETS) } } },
} satisfies Meta<typeof SelectionField>;

export default meta;
type Story = StoryObj<typeof meta>;

/** Nothing chosen yet, so the field offers the history's first dataset. */
export const NothingSelected: Story = {};

/** A dataset the directive already names. */
export const DatasetSelected: Story = {
    args: { objectId: HISTORY_DATASETS[2].id, objectName: HISTORY_DATASETS[2].name },
};

/** The current history has no datasets yet. */
export const EmptyHistory: Story = {
    parameters: { msw: { handlers: { datasets: currentHistoryDatasets([]) } } },
};

/** The current history belongs to someone else and isn't shared. */
export const HistoryNotAccessible: Story = {
    parameters: {
        msw: {
            handlers: {
                datasets: http.get("/api/datasets", ({ response }) =>
                    response("4XX").json(
                        { err_msg: "History is not accessible by user", err_code: 403002 },
                        { status: 403 },
                    ),
                ),
            },
        },
    },
};

const WORKFLOW_LABELS: OptionType[] = [
    { id: "forward_reads", name: "forward_reads (input)" },
    { id: "gene_counts", name: "gene_counts (output)" },
];

/** In a workflow's report template, the choices are the workflow's input and output labels. */
export const WorkflowLabels: Story = {
    args: { objectQuery: async () => WORKFLOW_LABELS },
};
