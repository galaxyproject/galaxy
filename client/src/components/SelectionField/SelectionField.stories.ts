import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { withCurrentHistory } from "@tests/test-data/currentHistory";
import { expectOptions } from "@tests/test-data/multiselect";
import { exactly } from "@tests/test-data/text";
import { expect, within } from "storybook/test";

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

type PlayContext = Parameters<NonNullable<Story["play"]>>[0];

const DATASET_NAMES = HISTORY_DATASETS.map((dataset) => dataset.name);

/** Waits for the picker, which shows once the first search has answered, and checks the one value it shows. */
async function seeChosen({ canvas, step }: PlayContext, name: string) {
    await step(`See "${name}" chosen`, async () => {
        const combobox = await canvas.findByRole("combobox", {}, { timeout: 5000 });
        // The combobox is the picker's search input; the chosen value shows in the picker around it.
        const picker = combobox.closest<HTMLElement>('[role="group"]')!;
        await expect(picker).toHaveTextContent(exactly(name));
        await expect(within(picker).getByText(name)).toBeVisible();
    });
}

/** Waits for the alert shown instead of the picker and reads its whole text. */
async function seeAlertInstead({ canvas, step }: PlayContext, text: RegExp) {
    await step("See an alert instead of the picker", async () => {
        await expect(await canvas.findByRole("alert", {}, { timeout: 5000 })).toHaveTextContent(text);
        await expect(canvas.queryByRole("combobox")).not.toBeInTheDocument();
    });
}

/** Nothing chosen yet, so the field offers the history's first dataset. */
export const NothingSelected: Story = {
    play: (context) => seeChosen(context, HISTORY_DATASETS[0].name),
};

/** Opening the picker lists the current history's datasets, oldest first. */
export const ListsHistoryDatasets: Story = {
    play: async (context) => {
        await seeChosen(context, HISTORY_DATASETS[0].name);
        await context.step("Open the list: the history's datasets, oldest first", async () => {
            await expect(context.canvas.queryByRole("listbox")).not.toBeInTheDocument();
            // Pre-existing bug, tolerated here: the chosen dataset is a copy of its option, so
            // vue-multiselect marks no option selected (BUGS_FOUND).
            await expectOptions(context, DATASET_NAMES, { anyOf: [[], [HISTORY_DATASETS[0].name]] });
        });
    },

    // TODO a11y: aria-required-attr (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

/** A dataset the directive already names. */
export const DatasetSelected: Story = {
    args: { objectId: HISTORY_DATASETS[2].id, objectName: HISTORY_DATASETS[2].name },
    play: async (context) => {
        await seeChosen(context, HISTORY_DATASETS[2].name);
        await context.step("See the picker labelled by what it selects", async () => {
            const label = "Select a History Dataset Id:";
            await expect(context.canvas.getByText(exactly(label))).toBeVisible();
            await expect(context.canvas.getByRole("combobox", { name: label })).toBeInTheDocument();
        });
    },
};

/** The current history has no datasets yet. */
export const EmptyHistory: Story = {
    parameters: { msw: { handlers: { datasets: currentHistoryDatasets([]) } } },
    play: (context) =>
        seeAlertInstead(
            context,
            exactly(
                "No datasets found in your current history that are compatible. Please upload a compatible dataset.",
            ),
        ),
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
    // Pre-existing bug, tolerated here: the alert shows the thrown error's "Error: " prefix (BUGS_FOUND).
    play: (context) => seeAlertInstead(context, /^(Error: )?History is not accessible by user$/),
};

const WORKFLOW_LABELS: OptionType[] = [
    { id: "forward_reads", name: "forward_reads (input)" },
    { id: "gene_counts", name: "gene_counts (output)" },
];

/** In a workflow's report template, the choices are the workflow's input and output labels. */
export const WorkflowLabels: Story = {
    args: { objectQuery: async () => WORKFLOW_LABELS },
    play: (context) => seeChosen(context, WORKFLOW_LABELS[0]!.name),
};

/** Opening the picker in a report template lists the workflow's labels. */
export const ListsWorkflowLabels: Story = {
    args: { ...WorkflowLabels.args },
    play: async (context) => {
        await seeChosen(context, WORKFLOW_LABELS[0]!.name);
        await context.step("Open the list: the workflow's input and output labels", async () => {
            await expect(context.canvas.queryByRole("listbox")).not.toBeInTheDocument();
            // Pre-existing bug, tolerated here, as in `ListsHistoryDatasets`.
            await expectOptions(
                context,
                WORKFLOW_LABELS.map((label) => label.name),
                { anyOf: [[], [WORKFLOW_LABELS[0]!.name]] },
            );
        });
    },

    // TODO a11y: aria-required-attr (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};
