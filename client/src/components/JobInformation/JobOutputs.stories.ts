import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { getFakeCollectionSummary } from "@tests/test-data/collections";
import { getFakeDatasetDetails } from "@tests/test-data/datasets";
import { HttpResponse } from "msw";
import { expect, waitFor, within } from "storybook/test";

import type { HDCADetailed } from "@/api";
import { http } from "@/api/client/__mocks__/http";
import type { JobDisplayParametersSummary } from "@/api/jobs";
import { toolBoxState, withToolBoxState } from "@/components/Panels/test_fixtures";
import { CURRENT_HISTORY } from "@/components/SelectionField/test_fixtures";

import JobOutputs from "./JobOutputs.vue";

type Outputs = JobDisplayParametersSummary["outputs"];
const collectionId = "a6f93dfd72846d82";
const reportId = "f2db41e1fa331b3e";
const collectionOutputs: Outputs = {
    aligned_reads: [{ label: "Aligned reads", value: { id: collectionId, src: "hdca" } }],
};
const mixedOutputs: Outputs = {
    ...collectionOutputs,
    alignment_report: [{ label: "Alignment report", value: { id: reportId, src: "hda" } }],
    // Discovered primary files use this association name (job_execution/output_collect.py).
    "__new_primary_file_alignment_report|index__": [{ label: null, value: { id: "afec4c9cbdd0bf88", src: "hda" } }],
};
const reports = Array.from({ length: 15 }, (_, index) => {
    const number = String(index + 1).padStart(2, "0");
    return getFakeDatasetDetails({
        id: `cab310d9000000${number}`,
        hid: index + 3,
        history_id: CURRENT_HISTORY.id,
        name: `Quality report ${number}`,
    });
});
const manyOutputs: Outputs = Object.fromEntries(
    reports.map((report, index) => [
        `report_${index + 1}`,
        [{ label: report.name, value: { id: report.id, src: "hda" } }],
    ]),
);
const sampleReads = ["Sample A", "Sample B"].map((sample, index) =>
    getFakeDatasetDetails({
        id: `d902a3e06f52340${index}`,
        hid: index + 18,
        history_id: CURRENT_HISTORY.id,
        name: `${sample} aligned reads`,
    }),
);
const datasetReports = [
    ...sampleReads,
    getFakeDatasetDetails({ id: reportId, hid: 2, history_id: CURRENT_HISTORY.id, name: "Alignment summary" }),
    ...reports,
];
const collection = getFakeCollectionSummary({
    id: collectionId,
    collection_id: "a386d66e203128e6",
    hid: 1,
    history_id: CURRENT_HISTORY.id,
    name: "Aligned sample reads",
    element_count: 2,
    elements_states: { ok: 2 },
    contents_url: `/api/dataset_collections/${collectionId}/contents/a386d66e203128e6`,
    url: `/api/dataset_collections/${collectionId}`,
});

const collectionDetails: HDCADetailed = {
    ...collection,
    populated: true,
    elements: sampleReads.map((dataset, index) => ({
        id: `d5363c590eea714${index}`,
        element_identifier: `sample_${index + 1}`,
        element_index: index,
        element_type: "hda",
        model_class: "DatasetCollectionElement",
        object: dataset,
    })),
};

const meta = {
    title: "JobInformation/JobOutputs",
    component: JobOutputs,
    decorators: [withToolBoxState],
    args: { jobOutputs: collectionOutputs, title: "Job Outputs" },
    parameters: {
        ...toolBoxState({ tools: [], toolSections: { default: {} } }),
        msw: {
            handlers: {
                datasets: http.get("/api/datasets/{dataset_id}", ({ params, response }) => {
                    const dataset = datasetReports.find((report) => report.id === params.dataset_id);
                    if (!dataset) {
                        throw new Error(`Unexpected output dataset ${params.dataset_id}`);
                    }
                    return response.untyped(HttpResponse.json(dataset));
                }),
                collections: http.get("/api/dataset_collections/{hdca_id}", ({ params, request, response }) => {
                    if (params.hdca_id !== collection.id) {
                        throw new Error(`Unexpected output collection ${params.hdca_id}`);
                    }
                    return response(200).json(
                        new URL(request.url).searchParams.get("view") === "collection" ? collection : collectionDetails,
                    );
                }),
                objectStores: http.get("/api/object_stores", ({ response }) => response(200).json([])),
                entryPoints: http.untyped.get("/api/entry_points", () => HttpResponse.json([])),
            },
        },
    },
    afterEach: async ({ canvasElement, args }) => {
        const canvas = within(canvasElement);
        if (args.paginate) {
            await waitFor(() => expect(canvas.getAllByText("Quality report 01", { exact: true })).toHaveLength(2), {
                timeout: 5000,
            });
        } else {
            await waitFor(() => expect(canvas.getByText("Aligned sample reads", { exact: true })).toBeVisible(), {
                timeout: 5000,
            });
        }
    },
} satisfies Meta<typeof JobOutputs>;
export default meta;
type Story = StoryObj<typeof meta>;

/** A job produces a list of aligned sample datasets. */
export const CollectionOutput: Story = {};

/** Dataset and collection outputs appear together; discovered primary files stay hidden. */
export const MixedOutputs: Story = { args: { jobOutputs: mixedOutputs, title: undefined } };

/** Fifteen separately named report outputs initially show ten, with a control to reveal the rest. */
export const ManyOutputs: Story = { args: { jobOutputs: manyOutputs, paginate: true } };
