import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { getFakeCollectionSummary } from "@tests/test-data/collections";
import { withCurrentUser } from "@tests/test-data/currentUser";
import { getFakeDatasetDetails } from "@tests/test-data/datasets";
import { http as rawHttp, HttpResponse } from "msw";

import { http } from "@/api/client/__mocks__/http";

import GenericItem from "./GenericItem.vue";

const meta = {
    title: "History/Content/GenericItem",
    component: GenericItem,
    decorators: [withCurrentUser()],
    args: { itemId: "item-id", itemSrc: "hda" },
    parameters: {
        msw: {
            handlers: {
                objectStores: http.get("/api/object_stores", ({ response }) => response(200).json([])),
            },
        },
    },
} satisfies Meta<typeof GenericItem>;

export default meta;
type Story = StoryObj<typeof meta>;

export const RunningDataset: Story = {
    parameters: {
        msw: {
            handlers: {
                item: http.get("/api/datasets/{dataset_id}", ({ params, response }) =>
                    response.untyped(
                        HttpResponse.json(
                            getFakeDatasetDetails({
                                id: params.dataset_id,
                                name: "Alignment output",
                                state: "running",
                            }),
                        ),
                    ),
                ),
            },
        },
    },
};

export const PopulatingCollection: Story = {
    args: { itemSrc: "hdca" },
    parameters: {
        msw: {
            handlers: {
                item: http.get("/api/dataset_collections/{hdca_id}", ({ params, response }) =>
                    response(200).json(
                        getFakeCollectionSummary({
                            id: params.hdca_id,
                            name: "Alignment collection",
                            populated_state: "new",
                            element_count: 2,
                        }),
                    ),
                ),
            },
        },
    },
};

export const DatasetAccessDenied: Story = {
    parameters: {
        msw: {
            handlers: {
                item: http.get("/api/datasets/{dataset_id}", ({ response }) =>
                    response.untyped(
                        HttpResponse.json(
                            {
                                err_code: 403002,
                                err_msg: "HistoryDatasetAssociation is not accessible by user",
                            },
                            { status: 403 },
                        ),
                    ),
                ),
            },
        },
    },
};

export const CollectionHistoryAccessDenied: Story = {
    args: { itemSrc: "hdca" },
    parameters: {
        msw: {
            handlers: {
                item: http.get("/api/dataset_collections/{hdca_id}", ({ response }) =>
                    response("4XX").json(
                        { err_code: 403002, err_msg: "History is not accessible by user" },
                        { status: 403 },
                    ),
                ),
            },
        },
    },
};

export const DatasetNetworkFailure: Story = {
    parameters: {
        msw: { handlers: { item: rawHttp.get("/api/datasets/:dataset_id", () => HttpResponse.error()) } },
    },
};

export const CollectionNetworkFailure: Story = {
    args: { itemSrc: "hdca" },
    parameters: {
        msw: { handlers: { item: rawHttp.get("/api/dataset_collections/:hdca_id", () => HttpResponse.error()) } },
    },
};
