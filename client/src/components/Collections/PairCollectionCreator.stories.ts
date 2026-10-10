import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { h } from "vue";

import type { HDASummary } from "@/api";

import { collectionCreatorHandlers, CreatorWithHistory, READ_PAIR } from "./test_fixtures";

import PairCollectionCreator from "./PairCollectionCreator.vue";

type Args = Omit<InstanceType<typeof PairCollectionCreator>["$props"], "initialElements"> & { history: HDASummary[] };

// No `component`: the harness feeds `initialElements` from `history`.
const meta = {
    title: "Collections/PairCollectionCreator",
    render:
        ({ history, ...args }) =>
        () =>
            h(CreatorWithHistory, { creator: PairCollectionCreator, history, ...args }),
    parameters: { msw: { handlers: collectionCreatorHandlers } },
    args: {
        historyId: "history-1",
        mode: "modal",
        history: [...READ_PAIR],
    },
} satisfies Meta<Args>;

export default meta;
type Story = StoryObj<typeof meta>;

/** Building a pair from a history holding a run's forward and reverse reads, neither picked yet. */
export const ReadPairInHistory: Story = {};

/** Nothing in the history to pair. */
export const EmptyHistory: Story = { args: { history: [] } };
