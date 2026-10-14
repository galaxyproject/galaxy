import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { withCurrentUser } from "@tests/test-data/currentUser";

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

/** A dataset-list input whose runtime datatype filters follow the connected workflow steps. */
export const DatasetList: Story = {};

/** Paired reads accompanied by a required Condition column in the sample sheet. */
export const PairedSampleSheet: Story = {
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
