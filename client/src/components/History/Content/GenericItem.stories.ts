import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { getFakeCollectionSummary } from "@tests/test-data/collections";
import { withCurrentUser } from "@tests/test-data/currentUser";
import { getFakeDatasetDetails } from "@tests/test-data/datasets";
import { http as rawHttp, HttpResponse } from "msw";
import { expect } from "storybook/test";

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
    play: async ({ canvas, step }) => {
        await step("Read the fetched dataset", async () => {
            await expect(await canvas.findByText("Alignment output", { exact: true }, { timeout: 5000 })).toBeVisible();
            await expect(canvas.queryByRole("alert")).not.toBeInTheDocument();
            await expect(canvas.queryByText("Loading dataset", { exact: true })).not.toBeInTheDocument();
        });
    },
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
    play: async ({ canvas, step }) => {
        await step("Read the fetched collection and its dataset count", async () => {
            await expect(
                await canvas.findByText("Alignment collection", { exact: true }, { timeout: 5000 }),
            ).toBeVisible();
            const description = canvas.getByText(/a list with 2/);
            await expect(description).toBeVisible();
            await expect(description).toHaveTextContent(/^a list with 2 txt datasets$/);
            await expect(canvas.queryByRole("alert")).not.toBeInTheDocument();
            await expect(canvas.queryByText("Loading dataset", { exact: true })).not.toBeInTheDocument();
        });
    },
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
    play: async ({ canvas, step }) => {
        await step("Explain why the dataset is inaccessible", async () => {
            await expect(await canvas.findByRole("alert", {}, { timeout: 5000 })).toHaveTextContent(
                /^HistoryDatasetAssociation is not accessible by user$/,
            );
            await expect(canvas.queryByText("Alignment output", { exact: true })).not.toBeInTheDocument();
            await expect(canvas.queryByText("Loading dataset", { exact: true })).not.toBeInTheDocument();
        });
    },
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
    play: async ({ canvas, step }) => {
        await step("Explain why the collection's history is inaccessible", async () => {
            await expect(await canvas.findByRole("alert", {}, { timeout: 5000 })).toHaveTextContent(
                /^History is not accessible by user$/,
            );
            await expect(canvas.queryByText("Alignment collection", { exact: true })).not.toBeInTheDocument();
            await expect(canvas.queryByText("Loading dataset", { exact: true })).not.toBeInTheDocument();
        });
    },
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
    play: async ({ canvas, step }) => {
        await step("Finish loading the dataset with a visible network error", async () => {
            const error = await canvas.findByRole("alert", {}, { timeout: 5000 });
            await expect(error).toBeVisible();
            await expect(error).toHaveTextContent(/^Failed to fetch$/);
            await expect(canvas.queryByText("Loading dataset", { exact: true })).not.toBeInTheDocument();
        });
    },
    parameters: {
        msw: { handlers: { item: rawHttp.get("/api/datasets/:dataset_id", () => HttpResponse.error()) } },
    },
};

export const CollectionNetworkFailure: Story = {
    play: async ({ canvas, step }) => {
        await step("Finish loading the collection with a visible network error", async () => {
            const error = await canvas.findByRole("alert", {}, { timeout: 5000 });
            await expect(error).toBeVisible();
            await expect(error).toHaveTextContent(/^Failed to fetch$/);
            await expect(canvas.queryByText("Loading dataset", { exact: true })).not.toBeInTheDocument();
        });
    },
    args: { itemSrc: "hdca" },
    parameters: {
        msw: { handlers: { item: rawHttp.get("/api/dataset_collections/:hdca_id", () => HttpResponse.error()) } },
    },
};
