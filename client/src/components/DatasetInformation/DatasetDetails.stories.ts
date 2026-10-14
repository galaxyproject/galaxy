import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { withCurrentUser } from "@tests/test-data/currentUser";
import { HttpResponse } from "msw";

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

/** Read an uploaded table, its original parameters, storage and completed creating job. */
export const CompletedDataset: Story = {
    parameters: { msw: { handlers: { ...datasetDetailsHandlers(), objectStores: selectableObjectStores([]) } } },
};

// The backend returns None without provenance; the detailed OpenAPI field currently omits null.
const noJobDataset: Omit<HDADetailed, "creating_job"> & { creating_job: null } = {
    ...DETAILS_DATASET,
    creating_job: null,
};

/** Legacy datasets can retain data and storage information without a recorded creating job. */
export const NoRecordedJob: Story = {
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
