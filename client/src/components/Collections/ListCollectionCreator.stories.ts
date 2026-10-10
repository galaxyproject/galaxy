import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { getFakeDatasetSummary } from "@tests/test-data/datasets";
import { seeToasts, withToasts } from "@tests/test-data/toasts";
import { expect, waitFor } from "storybook/test";
import { h } from "vue";

import type { HDASummary } from "@/api";
import { escapeRegExp } from "@/utils/regExp";

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
    decorators: [withToasts],
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

type PlayContext = Parameters<NonNullable<Story["play"]>>[0];
type Canvas = PlayContext["canvas"];

const CONTROL = "1: control (txt)";
const TREATED = "2: treated (txt)";
const RESCUED = "3: rescued (txt)";

/** The button that moves `dataset` into the list, named for the dataset's name alone. */
function selectButton(canvas: Canvas, dataset: string) {
    const name = { [CONTROL]: "control", [TREATED]: "treated", [RESCUED]: "rescued" }[dataset];
    return canvas.getByRole("button", { name: `Select ${name}` });
}

/**
 * Checks the datasets under a column's heading, in order, read as one text, and the count the
 * heading shows. Waits for them: the columns are worked out off the main thread.
 */
async function seeColumn(canvas: Canvas, heading: "Unselected" | "Selected", datasets: string[], timeout = 1000) {
    await waitFor(
        async () => {
            const title = canvas.getByText(heading);
            await expect(title).toHaveTextContent(
                new RegExp(`^${heading} \\(${datasets.length}\\) \\(Click name to edit\\)$`),
            );
            // The options sit in the list right after the heading's row.
            await expect(title.parentElement?.nextElementSibling).toHaveTextContent(
                new RegExp(`^${datasets.map(escapeRegExp).join(" ")}$`),
            );
        },
        { timeout },
    );
}

/** Moves datasets into the list, one click each, in the given order, from the `offered` ones. */
async function selectIntoList(
    { canvas, step, userEvent }: PlayContext,
    datasets: string[],
    offered: string[] = [TREATED, CONTROL],
) {
    await step(`Move ${datasets.join(", then ")} into the list`, async () => {
        await seeColumn(canvas, "Unselected", offered, 5000);
        await seeColumn(canvas, "Selected", []);
        for (const [index, dataset] of datasets.entries()) {
            await userEvent.click(selectButton(canvas, dataset));
            await seeColumn(canvas, "Selected", datasets.slice(0, index + 1));
        }
        await seeColumn(
            canvas,
            "Unselected",
            offered.filter((dataset) => !datasets.includes(dataset)),
        );
    });
}

/** Checks the list kept only the control dataset, and the user was told why the other left. */
async function seeTreatedDropped(canvas: Canvas, message: string) {
    await seeColumn(canvas, "Selected", [CONTROL]);
    await seeColumn(canvas, "Unselected", []);
    await seeToasts(canvas, [["Invalid element", message]]);
}

/** Building a list from a history of two datasets, none in the list yet. */
export const TwoDatasetsInHistory: Story = {
    // TODO a11y: color-contrast (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

/** A history poll reporting the same datasets again keeps the list in the user's order, without a word. */
export const KeepsListOnRefresh: Story = {
    // TODO a11y: aria-allowed-role, color-contrast, nested-interactive, target-size (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
    args: {
        history: [
            getFakeDatasetSummary({ id: "control-reads", hid: 1, name: "control" }),
            getFakeDatasetSummary({ id: "treated-reads", hid: 2, name: "treated" }),
            getFakeDatasetSummary({ id: "rescued-reads", hid: 3, name: "rescued" }),
        ],
    },
    play: async (context) => {
        const { canvas, step, userEvent } = context;
        await selectIntoList(context, [TREATED, CONTROL], [RESCUED, TREATED, CONTROL]);
        await step("Refresh the history", async () => {
            await userEvent.click(canvas.getByRole("button", { name: "Refresh history" }));
        });
        await step("Add the rescued dataset, and see the list kept in order with no notification", async () => {
            // The columns show the refreshed list only once worked out again, and this click's
            // result comes after the refresh's: the list must read in the user's order with it.
            // Keep these waits short: a toast from the refresh dismisses itself after 3s.
            await userEvent.click(selectButton(canvas, RESCUED));
            await seeColumn(canvas, "Selected", [TREATED, CONTROL, RESCUED]);
            await seeColumn(canvas, "Unselected", []);
            await seeToasts(canvas, []);
        });
    },
};

/** A dataset in the list leaves the history: the list drops it and a notification says so. */
export const DropsDeletedDataset: Story = {
    play: async (context) => {
        await selectIntoList(context, [CONTROL, TREATED]);
        await context.step("Delete the treated dataset from the history", async () => {
            await context.userEvent.click(context.canvas.getByRole("button", { name: "Delete treated" }));
            await seeTreatedDropped(context.canvas, "2: treated has been removed from the collection");
        });
    },

    // TODO a11y: aria-allowed-role, color-contrast, nested-interactive, target-size (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

/** A dataset in the list fails: the list drops it and a notification says why. */
export const DropsFailedDataset: Story = {
    play: async (context) => {
        await selectIntoList(context, [CONTROL, TREATED]);
        await context.step("Fail the treated dataset in the history", async () => {
            await context.userEvent.click(context.canvas.getByRole("button", { name: "Fail treated" }));
            await seeTreatedDropped(
                context.canvas,
                "2: treated has errored, is paused, or is not accessible and is not a valid element for this collection",
            );
        });
    },

    // TODO a11y: aria-allowed-role, color-contrast, nested-interactive, target-size (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

/** One dataset failed, so it isn't offered for the list. */
export const FailedDatasetInHistory: Story = {
    args: {
        history: [
            getFakeDatasetSummary({ id: "control-reads", hid: 1, name: "control" }),
            getFakeDatasetSummary({ id: "treated-reads", hid: 2, name: "treated", state: "error" }),
        ],
    },

    // TODO a11y: color-contrast (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

/** Nothing in the history to build a list from. */
export const EmptyHistory: Story = { args: { history: [] } };
