import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { h } from "vue";

import type { HDASummary } from "@/api";

import { collectionCreatorHandlers, CreatorWithHistory, fastqReads, READ_PAIR } from "./test_fixtures";

import PairedOrUnpairedListCollectionCreator from "./PairedOrUnpairedListCollectionCreator.vue";

type Args = Omit<InstanceType<typeof PairedOrUnpairedListCollectionCreator>["$props"], "initialElements"> & {
    history: HDASummary[];
    arriving?: HDASummary[];
};

const [FORWARD_READS, REVERSE_READS] = READ_PAIR;

// No `component`: the harness feeds `initialElements` from `history`.
const meta = {
    title: "Collections/PairedOrUnpairedListCollectionCreator",
    render:
        ({ history, arriving, ...args }) =>
        () =>
            h(CreatorWithHistory, { creator: PairedOrUnpairedListCollectionCreator, history, arriving, ...args }),
    parameters: { msw: { handlers: collectionCreatorHandlers } },
    args: {
        historyId: "history-1",
        mode: "modal",
        collectionType: "list:paired",
        history: [FORWARD_READS, REVERSE_READS],
    },
} satisfies Meta<Args>;

export default meta;
type Story = StoryObj<typeof meta>;

/**
 * Building a list of pairs from a history holding a run's forward and reverse reads, paired on
 * open by their `_1`/`_2` names. Another run's forward reads are still uploading.
 */
export const ReadPairInHistory: Story = {
    args: { arriving: [fastqReads("next-run-forward-reads", 3, "SRR1553426_1")] },
};

/** Opened on a history with nothing in it yet, while both mates of a run are still uploading. */
export const ReadPairStillUploading: Story = {
    args: {
        history: [],
        arriving: [
            fastqReads("forward-upload", 1, "SRR1553500.1.fastq"),
            fastqReads("reverse-upload", 2, "SRR1553500.2.fastq"),
        ],
    },
};

/**
 * The forward reads wait for their mate, which is still uploading, beside two reads whose names
 * match no pairing filter, so only a click can pair them.
 */
export const ForwardReadsAwaitingMate: Story = {
    args: {
        history: [
            FORWARD_READS,
            fastqReads("control-forward-reads", 3, "control_forward.fastq"),
            fastqReads("control-reverse-reads", 4, "control_reverse.fastq"),
        ],
        arriving: [REVERSE_READS],
    },
};
