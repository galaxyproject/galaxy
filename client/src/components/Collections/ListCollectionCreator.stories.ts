import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { getFakeDatasetSummary } from "@tests/test-data/datasets";
import { h } from "vue";

import type { HDASummary } from "@/api";

import { collectionCreatorHandlers, CreatorWithHistory } from "./test_fixtures";

import ListCollectionCreator from "./ListCollectionCreator.vue";

type Args = Omit<InstanceType<typeof ListCollectionCreator>["$props"], "initialElements"> & { history: HDASummary[] };

// No `component`: the harness feeds `initialElements` from `history`.
const meta = {
    title: "Collections/ListCollectionCreator",
    render:
        ({ history, ...args }) =>
        () =>
            h(CreatorWithHistory, { creator: ListCollectionCreator, history, ...args }),
    parameters: { msw: { handlers: collectionCreatorHandlers } },
    args: {
        historyId: "history-1",
        mode: "modal",
        history: [
            getFakeDatasetSummary({ id: "control-reads", hid: 1, name: "control" }),
            getFakeDatasetSummary({ id: "treated-reads", hid: 2, name: "treated" }),
        ],
    },
} satisfies Meta<Args>;

export default meta;
type Story = StoryObj<typeof meta>;

/** Building a list from a history of two datasets, none in the list yet. */
export const TwoDatasetsInHistory: Story = {};

/** One dataset failed, so it isn't offered for the list. */
export const FailedDatasetInHistory: Story = {
    args: {
        history: [
            getFakeDatasetSummary({ id: "control-reads", hid: 1, name: "control" }),
            getFakeDatasetSummary({ id: "treated-reads", hid: 2, name: "treated", state: "error" }),
        ],
    },
};

/** Nothing in the history to build a list from. */
export const EmptyHistory: Story = { args: { history: [] } };
