import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { seeToasts, withToasts } from "@tests/test-data/toasts";
import { expect, waitFor, within } from "storybook/test";
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
    decorators: [withToasts],
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

type PlayContext = Parameters<NonNullable<Story["play"]>>[0];
type Canvas = PlayContext["canvas"];

const PAIR = "FORWARD 1: SRR1553425_1 REVERSE 2: SRR1553425_2";
const FORWARD = "UNPAIRED 1: SRR1553425_1 (fastqsanger)";
const REVERSE = "UNPAIRED 2: SRR1553425_2 (fastqsanger)";
const CONTROL_FORWARD = "UNPAIRED 3: control_forward.fastq (fastqsanger)";
const CONTROL_REVERSE = "UNPAIRED 4: control_reverse.fastq (fastqsanger)";
const CONTROL_PAIR = "FORWARD 3: control_forward.fastq REVERSE 4: control_reverse.fastq";

/** The grid's rows in display order; the DOM keeps AG Grid's own order. */
function gridRows(canvas: Canvas) {
    return canvas
        .queryAllByRole("row")
        .filter((row) => within(row).queryAllByRole("gridcell").length)
        .sort((a, b) => Number(a.getAttribute("aria-rowindex")) - Number(b.getAttribute("aria-rowindex")));
}

/** A row's first cell, which names its datasets. */
function datasetsCell(row: HTMLElement) {
    return within(row).getAllByRole("gridcell")[0]!;
}

/** What a row's datasets cell reads, as one line. */
function datasetsText(row: HTMLElement) {
    return datasetsCell(row).textContent?.replace(/\s+/g, " ").trim();
}

/** Checks the grid's rows, in order, by their datasets. Waits, since AG Grid renders on its own schedule. */
async function seeRows(canvas: Canvas, rows: string[], timeout = 1000) {
    await waitFor(
        async () => {
            await expect(gridRows(canvas).map(datasetsText)).toEqual(rows);
        },
        { timeout },
    );
}

/**
 * Clicks an unpaired row's link icon, which picks it to pair by click, or pairs it with the one
 * picked before. The icon is hidden from assistive tech and has no name or role of its own
 * (BUGS_FOUND), so it's found as the cell's hidden image that draws a link.
 */
async function clickLink({ canvas, userEvent }: PlayContext, row: string) {
    const found = gridRows(canvas).find((candidate) => datasetsText(candidate) === row);
    await expect(found).toBeDefined();
    const link = within(datasetsCell(found!))
        .getAllByRole("img", { hidden: true })
        .find((image) => image.getAttribute("data-icon") === "link");
    await userEvent.click(link!);
}

/** Clicks one of the history's controls, as a history poll reporting that change. */
async function changeHistory({ canvas, userEvent }: PlayContext, label: string) {
    await userEvent.click(canvas.getByRole("button", { name: label }));
}

/**
 * Building a list of pairs from a history holding a run's forward and reverse reads, paired on
 * open by their `_1`/`_2` names. Another run's forward reads are still uploading.
 */
export const ReadPairInHistory: Story = {
    args: { arriving: [fastqReads("next-run-forward-reads", 3, "SRR1553426_1")] },
    play: async ({ canvas, step }) => {
        await step("See the run's reads paired on open", async () => {
            await seeRows(canvas, [PAIR], 5000);
        });
    },
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

/** Mates that finish uploading one at a time are paired once the second arrives. */
export const PairsMatesAsTheyArrive: Story = {
    ...ReadPairStillUploading,
    play: async (context) => {
        const { canvas, step } = context;
        await step("The forward reads arrive: listed unpaired", async () => {
            await changeHistory(context, "Add SRR1553500.1.fastq");
            await seeRows(canvas, ["UNPAIRED 1: SRR1553500.1.fastq (fastqsanger)"], 5000);
        });
        await step("The reverse reads arrive: paired with them", async () => {
            await changeHistory(context, "Add SRR1553500.2.fastq");
            await seeRows(canvas, ["FORWARD 1: SRR1553500.1.fastq REVERSE 2: SRR1553500.2.fastq"]);
        });
    },
};

/** Picks the waiting forward reads to pair by click, then lets `change` happen in the history. */
async function pickForwardThenChange(context: PlayContext, change: string, rows: string[]) {
    await context.step(`Pick the forward reads to pair, then "${change}" in the history`, async () => {
        await seeRows(context.canvas, [FORWARD, CONTROL_FORWARD, CONTROL_REVERSE], 5000);
        await clickLink(context, FORWARD);
        await changeHistory(context, change);
        await seeRows(context.canvas, rows);
    });
}

/** Pairs the two controls by clicking each, and sees `rows`: the pick before the change is gone. */
async function clickPairControls(context: PlayContext, rows: string[]) {
    await context.step("Pair the controls by clicking each", async () => {
        await clickLink(context, CONTROL_FORWARD);
        await clickLink(context, CONTROL_REVERSE);
        await seeRows(context.canvas, rows);
    });
}

/** The forward reads picked for a click-pairing get auto-paired when their mate arrives; clicking starts over. */
export const ClickPairsAfterPickIsAutoPaired: Story = {
    ...ForwardReadsAwaitingMate,
    play: async (context) => {
        await pickForwardThenChange(context, "Add SRR1553425_2", [PAIR, CONTROL_FORWARD, CONTROL_REVERSE]);
        await clickPairControls(context, [PAIR, CONTROL_PAIR]);
    },
};

/** The forward reads picked for a click-pairing leave the history; clicking starts over. */
export const ClickPairsAfterPickIsDeleted: Story = {
    ...ForwardReadsAwaitingMate,
    play: async (context) => {
        await pickForwardThenChange(context, "Delete SRR1553425_1", [CONTROL_FORWARD, CONTROL_REVERSE]);
        await clickPairControls(context, [CONTROL_PAIR]);
    },
};

/** The reverse reads leave the history: the forward reads stay, unpaired, with a warning. */
export const WarnsWhenMateLeaves: Story = {
    ...ReadPairInHistory,
    play: async (context) => {
        const { canvas, step } = context;
        await step("Delete the reverse reads from the history", async () => {
            await seeRows(canvas, [PAIR], 5000);
            await changeHistory(context, "Delete SRR1553425_2");
            // Right away: the toast dismisses itself after 3s.
            await seeToasts(canvas, [
                ["Dataset unavailable", "2: SRR1553425_2 is no longer available and was removed from the pairing list"],
            ]);
            await seeRows(canvas, [FORWARD]);
        });
    },
};

/** Both reads leave the history at once: one notification names the pair. */
export const DropsVanishedPair: Story = {
    ...ReadPairInHistory,
    play: async (context) => {
        const { canvas, step } = context;
        await step("Empty the history", async () => {
            await seeRows(canvas, [PAIR], 5000);
            await changeHistory(context, "Delete all");
            // Right away: the toast dismisses itself after 3s.
            await seeToasts(canvas, [
                ["Invalid element", "1: SRR1553425_1, 2: SRR1553425_2 has been removed from the collection"],
            ]);
            await expect(await canvas.findByText(/^No items available to create a collection\./)).toBeVisible();
            await seeRows(canvas, []);
        });
    },
};

/** Datasets the user discarded stay discarded when the history reports them again. */
export const ForgetsDiscardedDatasets: Story = {
    ...ReadPairInHistory,
    play: async (context) => {
        const { canvas, step, userEvent } = context;
        await step("Delete the reverse reads, then discard the forward reads left unpaired", async () => {
            await seeRows(canvas, [PAIR], 5000);
            await changeHistory(context, "Delete SRR1553425_2");
            await seeRows(canvas, [FORWARD]);
            await userEvent.click(canvas.getByText("Click here to discard all remaining unpaired datasets."));
            await seeRows(canvas, []);
        });
        await step("The reverse reads come back: only they are listed", async () => {
            await changeHistory(context, "Add SRR1553425_2");
            await seeRows(canvas, [REVERSE]);
        });
    },
};
