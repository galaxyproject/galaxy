import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { getFakeCollectionSummary } from "@tests/test-data/collections";
import { getFakeDatasetDetails } from "@tests/test-data/datasets";
import { HttpResponse } from "msw";
import { expect, userEvent, waitFor, within } from "storybook/test";

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
export const CollectionOutput: Story = {
    play: async ({ canvasElement, step }) => {
        const canvas = within(canvasElement);
        await step("Distinguish the tool output label from the collection's name", async () => {
            await canvas.findByRole("heading", { name: "Job Outputs" }, { timeout: 5000 });
            const rows = within(canvas.getByRole("table")).getAllByRole("row").slice(1);
            expect(rows).toHaveLength(1);
            const cells = within(rows[0]!).getAllByRole("cell");
            expect(cells[0]?.textContent?.trim()).toBe("Aligned reads");
            expect(
                await within(cells[1]!).findByText("Aligned sample reads", { exact: true }, { timeout: 5000 }),
            ).toBeVisible();
        });
    },
};

/** Dataset and collection outputs appear together; discovered primary files stay hidden. */
export const MixedOutputs: Story = {
    args: { jobOutputs: mixedOutputs, title: undefined },
    play: async ({ canvasElement, step }) => {
        const canvas = within(canvasElement);
        await step("Show the visible collection and dataset in tool output order", async () => {
            await canvas.findByText("Aligned sample reads", { exact: true }, { timeout: 5000 });
            const rows = within(canvas.getByRole("table")).getAllByRole("row").slice(1);
            expect(rows).toHaveLength(2);
            const collectionCells = within(rows[0]!).getAllByRole("cell");
            const datasetCells = within(rows[1]!).getAllByRole("cell");
            expect(collectionCells[0]?.textContent?.trim()).toBe("Aligned reads");
            expect(datasetCells[0]?.textContent?.trim()).toBe("Alignment report");
            expect(
                await within(collectionCells[1]!).findByText(
                    "Aligned sample reads",
                    { exact: true },
                    { timeout: 5000 },
                ),
            ).toBeVisible();
            datasetCells[1]!.scrollIntoView({ behavior: "instant", block: "center" });
            expect(
                await within(datasetCells[1]!).findByText("Alignment summary", { exact: true }, { timeout: 5000 }),
            ).toBeVisible();
        });
    },
};

/** Fifteen separately named report outputs initially show ten, with a control to reveal the rest. */
export const ManyOutputs: Story = { args: { jobOutputs: manyOutputs, paginate: true } };

export const RevealsAllReports: Story = {
    ...ManyOutputs,
    play: async ({ canvasElement, step }) => {
        const canvas = within(canvasElement);
        const reportNames = Array.from(
            { length: 15 },
            (_, index) => `Quality report ${String(index + 1).padStart(2, "0")}`,
        );
        await step("Start with the first ten reports in order", async () => {
            await canvas.findByRole("heading", { name: "Job Outputs (showing 10 of 15)" }, { timeout: 5000 });
            const rows = within(canvas.getByRole("table")).getAllByRole("row").slice(1, -1);
            expect(rows.map((row) => within(row).getAllByRole("cell")[0]?.textContent?.trim())).toEqual(
                reportNames.slice(0, 10),
            );
            expect(canvas.getByRole("button", { name: "Show 5 more outputs" })).toBeVisible();
        });
        await step("Reveal the remaining reports and load each actual dataset", async () => {
            const reveal = canvas.getByRole("button", { name: "Show 5 more outputs" });
            reveal.scrollIntoView({ behavior: "instant", block: "center" });
            await userEvent.click(reveal);
            await canvas.findByRole("heading", { name: "Job Outputs" });
            const rows = within(canvas.getByRole("table")).getAllByRole("row").slice(1);
            expect(rows.map((row) => within(row).getAllByRole("cell")[0]?.textContent?.trim())).toEqual(reportNames);
            expect(canvas.queryByRole("button", { name: /Show .* more outputs/ })).not.toBeInTheDocument();
            for (const [index, row] of rows.entries()) {
                const cell = within(row).getAllByRole("cell")[1]!;
                cell.scrollIntoView({ behavior: "instant", block: "center" });
                expect(
                    await within(cell).findByText(reportNames[index]!, { exact: true }, { timeout: 5000 }),
                ).toBeVisible();
            }
        });
    },
};
