import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { getFakeHistorySummaryExtended } from "@tests/test-data";
import { withCurrentHistory } from "@tests/test-data/currentHistory";
import { http as rawHttp, HttpResponse } from "msw";
import { expect, waitFor, within } from "storybook/test";

import { http } from "@/api/client/__mocks__/http";
import type { FormInputNode } from "@/components/Form/composables/useFormState";
import { TOOLBOX_USER, toolBoxState, withToolBoxState } from "@/components/Panels/test_fixtures";
import { CURRENT_HISTORY } from "@/components/SelectionField/test_fixtures";

import DatasetAttributes from "./DatasetAttributes.vue";

const bedId = "f2db41e1fa331b3e";
const textId = "afec4c9cbdd0bf88";
const uploadingId = "cab310d912da5101";
const uploadMessage = "Please wait until this dataset finishes uploading before attempting to edit its metadata.";
const privateRole = "a386d66e203128e6";
const history = getFakeHistorySummaryExtended({ ...CURRENT_HISTORY, user_id: TOOLBOX_USER.id });
type EditInput = FormInputNode & { area?: boolean; readonly?: boolean; multiple?: boolean };

/** Legacy /dataset/get_edit definitions come from controllers/dataset.py, not the tools API. */
function editForm(datasetId: string) {
    const bed = datasetId === bedId;
    const name = bed ? "Called peaks.bed" : "Analysis notes.txt";
    const attributeInputs: EditInput[] = [
        { name: "name", type: "text", label: "Name", value: name },
        { name: "info", type: "text", area: true, label: "Info", value: "Analysis output" },
        { name: "annotation", type: "text", area: true, label: "Annotation", optional: true, value: "" },
        {
            name: "dbkey",
            type: "select",
            label: "Database/Build",
            optional: true,
            multiple: false,
            options: [["unspecified (?)", "?", true]],
            value: null,
        },
    ];
    if (bed) {
        // Visible metadata inherited from Text/Tabular/Interval and declared by Bed.
        attributeInputs.push({
            name: "comment_lines",
            type: "text",
            label: "Number of comment lines",
            value: "0",
            readonly: false,
        });
        for (const [field, label, value] of [
            ["chromCol", "Chrom column", 1],
            ["startCol", "Start column", 2],
            ["endCol", "End column", 3],
            ["strandCol", "Strand column (click box & select)", 6],
            ["nameCol", "Name/Identifier column (click box & select)", 4],
            ["viz_filter_cols", "Score column for visualization", 5],
        ] as const) {
            attributeInputs.push({
                name: field,
                type: "select",
                label,
                value: null,
                multiple: field === "viz_filter_cols",
                optional: ["strandCol", "nameCol", "viz_filter_cols"].includes(field),
                options: Array.from({ length: 6 }, (_, index) => [String(index + 1), index + 1, index + 1 === value]),
            });
        }
    }
    return {
        display_name: name,
        message: null,
        status: null,
        dataset_id: datasetId,
        metadata_disable: false,
        attribute_inputs: attributeInputs,
        conversion_disable: !bed,
        // This converter is shipped in datatypes/converters/bed_to_gff_converter.xml.
        conversion_inputs: [
            {
                type: "select",
                name: "target_type",
                label: "Target datatype",
                options: bed ? [["gff (using 'Convert BED to GFF')", "gff"]] : [],
            },
        ],
        datatype_disable: false,
        datatype_inputs: [
            {
                type: "select",
                name: "datatype",
                label: "New Type",
                options: [
                    ["bed", "bed"],
                    ["gff", "gff"],
                    ["txt", "txt"],
                ],
                value: bed ? "bed" : "txt",
            },
        ],
        permission_disable: false,
        permission_inputs: [
            {
                type: "select",
                multiple: true,
                optional: true,
                name: "DATASET_ACCESS",
                label: "access",
                options: [[TOOLBOX_USER.email, privateRole]],
                value: [privateRole],
                readonly: false,
            },
            {
                type: "select",
                multiple: true,
                optional: true,
                name: "DATASET_MANAGE_PERMISSIONS",
                label: "manage permissions",
                options: [[TOOLBOX_USER.email, privateRole]],
                value: [privateRole],
                readonly: false,
            },
        ],
    };
}

const meta = {
    title: "DatasetInformation/DatasetAttributes",
    component: DatasetAttributes,
    decorators: [withCurrentHistory(history), withToolBoxState],
    args: { datasetId: bedId },
    parameters: {
        ...toolBoxState({ tools: [], toolSections: { default: {} } }),
        msw: {
            handlers: {
                edit: http.untyped.get("/dataset/get_edit", ({ request }) => {
                    const id = new URL(request.url).searchParams.get("dataset_id");
                    if (id !== bedId && id !== textId) {
                        throw new Error(`Unexpected editable dataset ${id}`);
                    }
                    return HttpResponse.json(editForm(id));
                }),
                save: http.untyped.put("/dataset/set_edit", async ({ request }) => {
                    const payload = (await request.json()) as {
                        dataset_id: string;
                        operation: string;
                        name?: string;
                        datatype?: string;
                        target_type?: string;
                    };
                    if (payload.dataset_id !== bedId && payload.dataset_id !== textId) {
                        throw new Error(`Unexpected saved dataset ${payload.dataset_id}`);
                    }
                    let message: string;
                    switch (payload.operation) {
                        case "attributes":
                            message = "Attributes updated.";
                            break;
                        case "autodetect":
                            message = "Auto-detect operation successfully submitted.";
                            break;
                        case "datatype":
                            message = `Changed the type to ${payload.datatype}.`;
                            break;
                        case "datatype_detect":
                            message = `Detection was finished and changed the datatype to ${payload.dataset_id === bedId ? "bed" : "txt"}.`;
                            break;
                        case "conversion":
                            if (payload.target_type !== "gff") {
                                throw new Error(`Unexpected converter ${payload.target_type}`);
                            }
                            message =
                                "The file conversion of Convert BED to GFF on data 1 has been added to the Queue.";
                            break;
                        case "permission":
                            message = "Your changes completed successfully.";
                            break;
                        default:
                            throw new Error(`Unsupported edit operation ${payload.operation}`);
                    }
                    return HttpResponse.json({ status: "success", message });
                }),
                currentHistory: http.untyped.get("/history/current_history_json", () => HttpResponse.json(history)),
            },
        },
    },
    afterEach: async ({ canvasElement, args }) => {
        const canvas = within(canvasElement);
        if (args.datasetId === uploadingId) {
            await waitFor(() => expect(canvas.getByRole("alert")).toHaveTextContent(uploadMessage), { timeout: 5000 });
        } else {
            await waitFor(() => expect(canvas.getByRole("textbox", { name: "Name" })).toBeVisible(), { timeout: 5000 });
        }
    },
} satisfies Meta<typeof DatasetAttributes>;
export default meta;
type Story = StoryObj<typeof meta>;

/** An owned BED dataset can edit metadata, change its datatype and manage role permissions. */
export const EditableBed: Story = {};

/** A plain text dataset has editable attributes and permissions but no datatype converters. */
export const TextWithoutConverters: Story = { args: { datasetId: textId } };

/** Uploading datasets reject edit-form loading until their upload finishes. */
export const UploadInProgress: Story = {
    args: { datasetId: uploadingId },
    parameters: {
        msw: {
            handlers: {
                edit: http.untyped.get("/dataset/get_edit", () =>
                    HttpResponse.json({ err_code: 0, err_msg: uploadMessage }, { status: 400 }),
                ),
            },
        },
    },
};

/** The edit form remains available when the save request loses its network connection. */
export const SaveNetworkFailure: Story = {
    parameters: { msw: { handlers: { save: rawHttp.put("/dataset/set_edit", () => HttpResponse.error()) } } },
};
