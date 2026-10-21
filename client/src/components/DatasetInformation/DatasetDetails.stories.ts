import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { withCurrentUser } from "@tests/test-data/currentUser";
import { HttpResponse } from "msw";
import { expect } from "storybook/test";

import type { HDADetailed } from "@/api";
import { http } from "@/api/client/__mocks__/http";

import { selectableObjectStores } from "../ObjectStore/test_fixtures";
import { datasetDetailsHandlers, datasetStorageHandler, DETAILS_DATASET } from "./test_fixtures";

import DatasetDetails from "./DatasetDetails.vue";

const meta = {
    title: "DatasetInformation/DatasetDetails",
    component: DatasetDetails,
    decorators: [withCurrentUser()],
    args: { datasetId: DETAILS_DATASET.id },
} satisfies Meta<typeof DatasetDetails>;
export default meta;
type Story = StoryObj<typeof meta>;
type PlayContext = Parameters<NonNullable<Story["play"]>>[0];

async function readDataset(context: PlayContext) {
    await expect(
        await context.canvas.findByRole("heading", { name: "Dataset Information" }, { timeout: 5000 }),
    ).toBeVisible();
    await expect(context.canvas.getByRole("cell", { name: DETAILS_DATASET.name! })).toBeVisible();
}

/** Read an uploaded table, its original parameters, storage and completed creating job. */
export const CompletedDataset: Story = {
    play: async (context) => {
        await context.step("Read the dataset and its sanitized tabular peek", async () => {
            await readDataset(context);
            await expect(context.canvas.getByRole("heading", { name: "Dataset Peek" })).toBeVisible();
            await expect(context.canvas.getByRole("columnheader", { name: "sample" })).toBeVisible();
            await expect(context.canvas.getByRole("columnheader", { name: "reads" })).toBeVisible();
            await expect(context.canvas.getByRole("cell", { name: "Sample A" })).toBeVisible();
            await expect(context.canvas.getByRole("cell", { name: "18420" })).toBeVisible();
        });
    },
    parameters: { msw: { handlers: { ...datasetDetailsHandlers(), objectStores: selectableObjectStores([]) } } },
};

// The backend returns None without provenance; the detailed OpenAPI field currently omits null.
const noJobDataset: Omit<HDADetailed, "creating_job"> & { creating_job: null } = {
    ...DETAILS_DATASET,
    creating_job: null,
};

/** Legacy datasets can retain data and storage information without a recorded creating job. */
export const NoRecordedJob: Story = {
    play: async (context) => {
        await context.step("Read the dataset without recorded job provenance", async () => {
            await readDataset(context);
            await expect(context.canvas.getByRole("heading", { name: "Job Not Found" })).toBeVisible();
            await expect(
                context.canvas.getByText(
                    "No job associated with this dataset is recorded in Galaxy. Galaxy cannot determine full dataset provenance and history for this dataset.",
                    { exact: true },
                ),
            ).toBeVisible();
            await expect(context.canvas.queryByRole("heading", { name: "Dataset Peek" })).not.toBeInTheDocument();
        });
    },
    parameters: {
        msw: {
            handlers: {
                dataset: http.get("/api/datasets/{dataset_id}", ({ params, response }) =>
                    params.dataset_id === noJobDataset.id
                        ? response.untyped(HttpResponse.json(noJobDataset))
                        : response("4XX").json({ err_msg: "Dataset not found", err_code: 404001 }, { status: 404 }),
                ),
                storage: datasetStorageHandler(noJobDataset.id),
                objectStores: selectableObjectStores([]),
            },
        },
    },
};

const originalPeekDataset: HDADetailed = {
    ...DETAILS_DATASET,
    peek: "<table><tr><td>col1</td></tr></table>",
};

/** The unit's original col1 vector also renders visibly through the real sanitizer. */
export const ReadsOriginalPeek: Story = {
    parameters: {
        msw: {
            handlers: {
                ...datasetDetailsHandlers(),
                dataset: http.get("/api/datasets/{dataset_id}", ({ params, response }) =>
                    params.dataset_id === originalPeekDataset.id
                        ? response.untyped(HttpResponse.json(originalPeekDataset))
                        : response("4XX").json({ err_msg: "Dataset not found", err_code: 404001 }, { status: 404 }),
                ),
                objectStores: selectableObjectStores([]),
            },
        },
    },
    play: async (context) => {
        await context.step("Read the original col1 peek through real sanitization", async () => {
            await readDataset(context);
            await expect(context.canvas.getByRole("heading", { name: "Dataset Peek" })).toBeVisible();
            await expect(context.canvas.getByRole("cell", { name: "col1" })).toBeVisible();
        });
    },
};
