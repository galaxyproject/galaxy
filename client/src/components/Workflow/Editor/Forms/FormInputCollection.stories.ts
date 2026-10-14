import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { withCurrentUser } from "@tests/test-data/currentUser";
import { openOptions, pickOption } from "@tests/test-data/multiselect";
import { expect, waitFor, within } from "storybook/test";

import { testDatatypesMapper } from "@/components/Datatypes/test_fixtures";
import type { Step } from "@/stores/workflowStepStore";

import { createTestStep } from "../test_fixtures";

import FormInputCollection from "./FormInputCollection.vue";

const datasetListStep: Step = {
    ...createTestStep(3),
    id: 3,
    type: "data_collection_input",
    name: "Input dataset collection",
    label: "Read collections",
    outputs: [
        {
            name: "output",
            extensions: ["input"],
            optional: false,
            collection: true,
            collection_type: "list",
            collection_type_source: null,
        },
    ],
    tool_state: {
        collection_type: JSON.stringify("list"),
        optional: "false",
        tag: "null",
        format: "null",
        fields: "null",
        column_definitions: "null",
    },
};

const meta = {
    title: "Workflow/Editor/Forms/FormInputCollection",
    component: FormInputCollection,
    decorators: [withCurrentUser()],
    args: { step: datasetListStep, datatypes: testDatatypesMapper.datatypes },
} satisfies Meta<typeof FormInputCollection>;

export default meta;
type Story = StoryObj<typeof meta>;

/** Scope the shared picker helpers away from the separate datatype combobox. */
function collectionPicker(context: Parameters<typeof openOptions>[0]) {
    const input = context.canvas.getByRole("combobox", { name: "Collection type" });
    return { ...context, canvas: within(input.closest<HTMLElement>(".form-collection-type")!) };
}

/** Read the selected collection type through the picker’s visible, selected option. */
async function seeCollectionType(context: Parameters<typeof openOptions>[0], label: string) {
    const list = await openOptions(collectionPicker(context));
    await expect(within(list).getByRole("option", { name: label, selected: true })).toBeVisible();
    await context.userEvent.click(context.canvas.getByRole("combobox", { name: "Collection type" }));
}

/** A dataset-list input whose runtime datatype filters follow the connected workflow steps. */
export const DatasetList: Story = {
    play: async (context) => {
        const { canvas, step } = context;
        await step("Read the collection type stored on the workflow input", async () => {
            const collectionType = canvas.getByRole("combobox", { name: "Collection type" });
            await expect(collectionType).toBeVisible();
            await seeCollectionType(context, "Flat List (list)");
            await expect(canvas.queryByText("Column definitions", { exact: true })).not.toBeInTheDocument();
        });
    },
};

/** Paired reads accompanied by a required Condition column in the sample sheet. */
export const PairedSampleSheet: Story = {
    play: async (context) => {
        const { canvas, step } = context;
        await step("Read the paired sample-sheet type and stored Condition column", async () => {
            const collectionType = canvas.getByRole("combobox", { name: "Collection type" });
            await expect(collectionType).toBeVisible();
            await seeCollectionType(context, "Sample Sheet of Paired Datasets (sample_sheet:paired)");
            await expect(canvas.getByText("Column definitions", { exact: true })).toBeVisible();
            const columnName = canvas.getByRole("textbox", { name: "Name" });
            await expect(columnName).toBeVisible();
            await expect(columnName).toHaveValue("Condition");
        });
    },
    args: {
        step: {
            ...datasetListStep,
            outputs: [
                {
                    name: "output",
                    extensions: ["input"],
                    optional: false,
                    collection_type: "sample_sheet:paired",
                    collection_type_source: null,
                    collection: true,
                },
            ],
            tool_state: {
                ...datasetListStep.tool_state,
                collection_type: JSON.stringify("sample_sheet:paired"),
                column_definitions: JSON.stringify([
                    { name: "Condition", type: "string", description: "", optional: false },
                ]),
            },
        },
    },
};

/** The author changes a plain list to a sample sheet and then returns to a plain list. */
export const ChangesCollectionType: Story = {
    play: async (context) => {
        const { canvas, step } = context;
        const collectionType = canvas.getByRole("combobox", { name: "Collection type" });
        await step("Start with a dataset list without sample-sheet columns", async () => {
            await expect(collectionType).toBeVisible();
            await seeCollectionType(context, "Flat List (list)");
            await expect(canvas.queryByText("Column definitions", { exact: true })).not.toBeInTheDocument();
        });
        await step("Reveal the sample-sheet column editor", async () => {
            await pickOption(collectionPicker(context), "Sample Sheet of Paired Datasets (sample_sheet:paired)");
            await waitFor(() => expect(canvas.getByText("Column definitions", { exact: true })).toBeVisible());
            await seeCollectionType(context, "Sample Sheet of Paired Datasets (sample_sheet:paired)");
            await expect(canvas.getByText("Add column.", { exact: true })).toBeVisible();
        });
        await step("Return to a list and remove the sample-sheet editor", async () => {
            await pickOption(collectionPicker(context), "Flat List (list)");
            await seeCollectionType(context, "Flat List (list)");
            await waitFor(() =>
                expect(canvas.queryByText("Column definitions", { exact: true })).not.toBeInTheDocument(),
            );
        });
    },
};
