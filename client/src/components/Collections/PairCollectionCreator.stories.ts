import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { NOTIFICATIONS, seeToasts, withToasts } from "@tests/test-data/toasts";
import { expect } from "storybook/test";
import { h } from "vue";

import type { HDASummary } from "@/api";
import { escapeRegExp } from "@/utils/regExp";

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
    decorators: [withToasts],
    parameters: { msw: { handlers: collectionCreatorHandlers } },
    args: {
        historyId: "history-1",
        mode: "modal",
        history: [...READ_PAIR],
    },
} satisfies Meta<Args>;

export default meta;
type Story = StoryObj<typeof meta>;

type PlayContext = Parameters<NonNullable<Story["play"]>>[0];
type Canvas = PlayContext["canvas"];

const FORWARD_READS = "1: SRR1553425_1 (fastqsanger)";
const REVERSE_READS = "2: SRR1553425_2 (fastqsanger)";

const SLOT_LABELS = {
    forward: "forward",
    // Until the app loads a locale (never, in Storybook), `localize` looks words up in an empty
    // array, so "reverse" returns `Array.prototype.reverse` and the label reads
    // "function reverse() { [native code] }:" (BUGS_FOUND).
    reverse: String.raw`(?:reverse|function reverse\(\) \{ \[native code\] \})`,
};

/** A side of the pair by its label; its whole text is the label, then the dataset in it. */
function pairSlot(canvas: Canvas, side: keyof typeof SLOT_LABELS) {
    return canvas.getByText(new RegExp(`^${SLOT_LABELS[side]}:$`));
}

/** Checks a side of the pair holds `dataset` (as the list names it), or nothing. */
async function seeInSlot(canvas: Canvas, side: keyof typeof SLOT_LABELS, dataset: string | null) {
    const content = dataset ? `${escapeRegExp(dataset)} Added to collection Remove` : "No dataset selected";
    await expect(pairSlot(canvas, side)).toHaveTextContent(new RegExp(`^${SLOT_LABELS[side]}: ${content}$`));
}

/** Picks the forward reads, then the reverse reads, into an empty pair. */
async function pickPair({ canvas, step, userEvent }: PlayContext) {
    await step("Pick the forward reads, then the reverse reads", async () => {
        await userEvent.click(await canvas.findByRole("button", { name: FORWARD_READS }));
        await seeInSlot(canvas, "forward", FORWARD_READS);
        await seeInSlot(canvas, "reverse", null);
        await userEvent.click(canvas.getByRole("button", { name: REVERSE_READS }));
        await seeInSlot(canvas, "forward", FORWARD_READS);
        await seeInSlot(canvas, "reverse", REVERSE_READS);
        await expect(canvas.getByRole("status")).toHaveTextContent(
            /^The Dataset Pair is ready to be created\. Provide a name and click the button below to create the pair\.$/,
        );
    });
}

/** Checks the reverse side was emptied, the forward side kept, and the user told why. */
async function seeReverseDropped(canvas: Canvas, message: string) {
    await seeInSlot(canvas, "forward", FORWARD_READS);
    await seeInSlot(canvas, "reverse", null);
    await seeToasts(canvas, [["Invalid element", message]]);
    const notifications = canvas.getByRole("region", { name: NOTIFICATIONS });
    const creatorAlerts = canvas.getAllByRole("alert").filter((alert) => !notifications.contains(alert));
    await expect(creatorAlerts).toHaveLength(1);
    await expect(creatorAlerts[0]).toHaveTextContent(/^Exactly two elements are needed for the pair\.$/);
}

/** Building a pair from a history holding a run's forward and reverse reads, neither picked yet. */
export const ReadPairInHistory: Story = {};

/** A history poll reporting the same datasets again keeps the pair, without a word. */
export const KeepsPairOnRefresh: Story = {
    play: async (context) => {
        const { canvas, step, userEvent } = context;
        await step("See both sides empty", async () => {
            await seeInSlot(canvas, "forward", null);
            await seeInSlot(canvas, "reverse", null);
        });
        await pickPair(context);
        await step("Refresh the history and see the pair kept", async () => {
            await userEvent.click(canvas.getByRole("button", { name: "Refresh history" }));
            await seeInSlot(canvas, "forward", FORWARD_READS);
            await seeInSlot(canvas, "reverse", REVERSE_READS);
        });
        await step("Swap the sides, and see no notification about the refresh", async () => {
            // The swap renders after the refresh did, so any toast it raised is on screen by now.
            await userEvent.click(canvas.getByRole("button", { name: "Swap" }));
            await seeInSlot(canvas, "forward", REVERSE_READS);
            await seeInSlot(canvas, "reverse", FORWARD_READS);
            await seeToasts(canvas, []);
        });
    },

    // TODO a11y: aria-allowed-role, nested-interactive (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

/** The reverse reads leave the history: their side empties and a notification says so. */
export const DropsDeletedDataset: Story = {
    play: async (context) => {
        await pickPair(context);
        await context.step("Delete the reverse reads from the history", async () => {
            await context.userEvent.click(context.canvas.getByRole("button", { name: "Delete SRR1553425_2" }));
            await seeReverseDropped(context.canvas, "2: SRR1553425_2 has been removed from the collection");
        });
    },

    // TODO a11y: aria-allowed-role, nested-interactive (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

/** The reverse reads fail: their side empties and a notification says why. */
export const DropsFailedDataset: Story = {
    play: async (context) => {
        await pickPair(context);
        await context.step("Fail the reverse reads in the history", async () => {
            await context.userEvent.click(context.canvas.getByRole("button", { name: "Fail SRR1553425_2" }));
            await seeReverseDropped(
                context.canvas,
                "2: SRR1553425_2 has errored, is paused, or is not accessible and is not a valid element for this collection",
            );
        });
    },

    // TODO a11y: aria-allowed-role, nested-interactive (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

/** Nothing in the history to pair. */
export const EmptyHistory: Story = { args: { history: [] } };
