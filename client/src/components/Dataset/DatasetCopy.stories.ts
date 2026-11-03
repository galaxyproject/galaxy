import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { withCurrentHistory } from "@tests/test-data/currentHistory";
import { exactly } from "@tests/test-data/text";
import { expect, waitFor, within } from "storybook/test";

import type { HistorySummary } from "@/api";
import { http } from "@/api/client/__mocks__/http";
import { escapeRegExp } from "@/utils/regExp";

import {
    DELETED_HISTORY,
    EMPTY_HISTORY,
    FORWARD_READS,
    HISTORY_CONTENTS,
    PAIRED_READS,
    REVERSE_READS,
    RNA_SEQ,
    VARIANT_CALLING,
} from "./test_fixtures";

import DatasetCopy from "./DatasetCopy.vue";

/** Lists the user's histories, as `/api/histories` does: deleted ones are left out. */
function historyList(histories: HistorySummary[]) {
    return http.get("/api/histories", ({ response }) => response(200).json(histories.filter((h) => !h.deleted)));
}

/** Answers each history's contents from `HISTORY_CONTENTS`. */
const historyContents = http.get("/api/histories/{history_id}/contents", ({ params, response }) =>
    response(200).json(HISTORY_CONTENTS[params.history_id] ?? []),
);

/** The history Galaxy creates for a copy into a new history. */
const NEW_HISTORY_ID = "2c7f9e4b1a8d0365";

/**
 * Copies as Galaxy does: into the named new history, or else the chosen ones. With neither, Galaxy
 * refuses, unless `withoutTarget` says to copy into the source history.
 */
function copyContents(withoutTarget: "refuse" | "copyIntoSource" = "refuse") {
    return http.post("/api/histories/{history_id}/copy_contents", async ({ params, request, response }) => {
        const { target_history_ids, target_history_name } = await request.json();
        if (target_history_name) {
            return response(200).json({ history_ids: [NEW_HISTORY_ID] });
        }
        if (target_history_ids?.length) {
            return response(200).json({ history_ids: target_history_ids });
        }
        if (withoutTarget === "copyIntoSource") {
            return response(200).json({ history_ids: [params.history_id] });
        }
        return response("4XX").json(
            { err_msg: "Select a destination history or provide a target history name.", err_code: 0 },
            { status: 400 },
        );
    });
}

/** The "Copy Datasets and Collections" page: pick items from a source history, then the histories to copy them to. */
const meta = {
    title: "Dataset/DatasetCopy",
    component: DatasetCopy,
    parameters: {
        msw: {
            handlers: {
                histories: historyList([RNA_SEQ, VARIANT_CALLING]),
                historyContents,
                copyContents: copyContents(),
            },
        },
    },
} satisfies Meta<typeof DatasetCopy>;

export default meta;
type Story = StoryObj<typeof meta>;

type PlayContext = Parameters<NonNullable<Story["play"]>>[0];

const RNA_SEQ_ITEMS = [FORWARD_READS, REVERSE_READS, PAIRED_READS].map(itemName);
const LISTED_HISTORIES = [RNA_SEQ.name, VARIANT_CALLING.name];
const REFUSED = "Select a destination history or provide a target history name.";

/** How the page names a history item: its number and name. */
function itemName(item: { hid: number; name?: string | null }) {
    return `${item.hid}: ${item.name}`;
}

/** The "From History" or "To History" column, found by its heading. */
function column({ canvas }: PlayContext, heading: "From History" | "To History") {
    return within(canvas.getByRole("heading", { name: heading }).parentElement!);
}

/** Checks a column's checkboxes, in order, and that none is ticked. */
async function expectUnticked(checkboxes: HTMLElement[], names: string[]) {
    await expect(checkboxes).toHaveLength(names.length);
    for (const [index, checkbox] of checkboxes.entries()) {
        await expect(checkbox).toHaveAccessibleName(names[index]);
        await expect(checkbox).not.toBeChecked();
    }
}

/** Waits for the source history's items and checks the source picker and every item, in order, unticked. */
async function seeSource(context: PlayContext, history: string, items: string[]) {
    await context.step(`See "${history}" as the source, offering ${items.join(", ")}`, async () => {
        const from = column(context, "From History");
        await from.findByRole("checkbox", { name: items[0] }, { timeout: 5000 });
        // The picker's combobox is its search input; the chosen history shows in the picker around it.
        const picker = from
            .getByRole("combobox", { name: "Select a Source History:" })
            .closest<HTMLElement>('[role="group"]')!;
        await expect(picker).toHaveTextContent(exactly(history));
        await expectUnticked(from.getAllByRole("checkbox"), items);
    });
}

/** Checks every listed history is offered as a target, unticked. */
async function seeTargets(context: PlayContext) {
    await context.step(`See every history offered as a target: ${LISTED_HISTORIES.join(", ")}`, async () => {
        await expectUnticked(column(context, "To History").getAllByRole("checkbox"), LISTED_HISTORIES);
    });
}

async function tickSource({ canvas, step, userEvent }: PlayContext, item: string) {
    await step(`Tick "${item}"`, async () => {
        await userEvent.click(await canvas.findByText(item, {}, { timeout: 5000 }));
    });
}

async function copy({ canvas, step, userEvent }: PlayContext) {
    await step('Click "Copy Selected Items"', async () => {
        await expect(canvas.queryByRole("alert")).not.toBeInTheDocument();
        await expect(canvas.queryByRole("status")).not.toBeInTheDocument();
        await userEvent.click(canvas.getByRole("button", { name: "Copy Selected Items" }));
    });
}

/** Checks the whole text of the error alert, or with `"status"` the success message, after copying. */
async function seeAlert({ canvas, step }: PlayContext, text: string | RegExp, role: "alert" | "status" = "alert") {
    await step(`See "${text}"`, async () => {
        await expect(await canvas.findByRole(role)).toHaveTextContent(typeof text === "string" ? exactly(text) : text);
    });
}

/** Checks the success message links each history copied to, in order, to its page. */
async function seeCopiedTo({ canvas, step }: PlayContext, histories: [name: string, id: string][]) {
    const names = histories.map(([name]) => name);
    await step(`See each history copied to linked: ${names.join(", ")}`, async () => {
        const links = within(await canvas.findByRole("status")).getAllByRole("link");
        await expect(links.map((link) => link.textContent?.trim())).toEqual(names);
        for (const [index, [, id]] of histories.entries()) {
            await expect(links[index]).toHaveAttribute("href", `/histories/view?id=${id}`);
        }
    });
}

/**
 * The current history, listed first, is the source: two reads and the pair built from them. Copying
 * with no target history chosen gets Galaxy's refusal.
 */
export const CopyFromCurrentHistory: Story = {
    decorators: [withCurrentHistory(RNA_SEQ)],
    play: async (context) => {
        await seeSource(context, RNA_SEQ.name, RNA_SEQ_ITEMS);
        await seeTargets(context);
        await context.step("See each history picker named by its caption", async () => {
            for (const [heading, caption] of [
                ["From History", "Select a Source History:"],
                ["To History", "Select a Target History:"],
            ] as const) {
                const side = column(context, heading);
                await expect(side.getByText(caption)).toBeVisible();
                await expect(side.getByRole("combobox", { name: caption })).toBeInTheDocument();
            }
        });
    },
};

/** The current history is the source wherever it sits in the list. */
export const CurrentHistoryListedSecond: Story = {
    decorators: [withCurrentHistory(VARIANT_CALLING)],
    play: (context) => seeSource(context, VARIANT_CALLING.name, HISTORY_CONTENTS[VARIANT_CALLING.id]!.map(itemName)),
};

/** A deleted current history isn't listed, so the first listed history is the source. */
export const CurrentHistoryNotListed: Story = {
    decorators: [withCurrentHistory(DELETED_HISTORY)],
    play: (context) => seeSource(context, RNA_SEQ.name, RNA_SEQ_ITEMS),
};

/** Without a current history, the first listed history is the source. */
export const NoCurrentHistory: Story = {
    play: (context) => seeSource(context, RNA_SEQ.name, RNA_SEQ_ITEMS),
};

/** The current history has nothing to copy yet. */
export const EmptyCurrentHistory: Story = {
    decorators: [withCurrentHistory(EMPTY_HISTORY)],
    parameters: { msw: { handlers: { histories: historyList([EMPTY_HISTORY, RNA_SEQ]) } } },
};

/** Copying with nothing selected asks for a selection instead. */
export const AsksForSelection: Story = {
    ...EmptyCurrentHistory,
    play: async (context) => {
        await context.step('See "This history has no datasets."', async () => {
            const from = column(context, "From History");
            await expect(await from.findByText("This history has no datasets.", {}, { timeout: 5000 })).toBeVisible();
        });
        await copy(context);
        await seeAlert(context, "Please select datasets and collections.");
    },
};

/** Ticking items and the "Select All" and "Unselect All" buttons. */
export const SelectsAndUnselectsEveryItem: Story = {
    ...CopyFromCurrentHistory,
    play: async (context) => {
        const { canvas, step, userEvent } = context;
        await seeSource(context, RNA_SEQ.name, RNA_SEQ_ITEMS);
        const items = () => column(context, "From History").getAllByRole("checkbox");
        await step('Click "Select All": every item ticked', async () => {
            await userEvent.click(canvas.getByRole("button", { name: "Select All" }));
            await waitFor(async () => {
                for (const item of items()) {
                    await expect(item).toBeChecked();
                }
            });
        });
        await step('Click "Unselect All": no item ticked', async () => {
            await userEvent.click(canvas.getByRole("button", { name: "Unselect All" }));
            await waitFor(async () => {
                for (const item of items()) {
                    await expect(item).not.toBeChecked();
                }
            });
        });
    },
};

/** Copying with no target history chosen shows Galaxy's refusal. */
export const ShowsCopyRefusal: Story = {
    ...CopyFromCurrentHistory,
    play: async (context) => {
        await tickSource(context, itemName(FORWARD_READS));
        await copy(context);
        await seeAlert(context, REFUSED);
    },
};

/** Copies an item into every ticked target history and links each of them. */
export const CopiesToTickedHistories: Story = {
    ...CopyFromCurrentHistory,
    play: async (context) => {
        const { step, userEvent } = context;
        await tickSource(context, itemName(FORWARD_READS));
        await step(`Tick the targets ${LISTED_HISTORIES.join(", ")}`, async () => {
            const to = column(context, "To History");
            for (const name of LISTED_HISTORIES) {
                await userEvent.click(to.getByText(name));
            }
        });
        await copy(context);
        // Pre-existing bug, tolerated here: a space shows before each comma between the histories (BUGS_FOUND).
        await seeAlert(
            context,
            new RegExp(`^1 item copied to: ${LISTED_HISTORIES.map(escapeRegExp).join(" ?, ")}$`),
            "status",
        );
        await seeCopiedTo(context, [
            [RNA_SEQ.name, RNA_SEQ.id],
            [VARIANT_CALLING.name, VARIANT_CALLING.id],
        ]);
    },
};

/**
 * Copies an item into a new history and links it. Pre-existing bug, tolerated here: the name input
 * has no label, only a caption beside it, so the play finds it from the caption (BUGS_FOUND).
 */
export const CopiesToNewHistory: Story = {
    ...CopyFromCurrentHistory,
    play: async (context) => {
        const { canvas, step, userEvent } = context;
        const name = "Reads for variant calling";
        await tickSource(context, itemName(FORWARD_READS));
        await step(`Name a new history "${name}"`, async () => {
            const input = canvas.getByText("Provide a New History Name:").nextElementSibling!;
            await userEvent.type(input, name);
        });
        await copy(context);
        await seeAlert(context, `1 item copied to: ${name}`, "status");
        await seeCopiedTo(context, [[name, NEW_HISTORY_ID]]);
    },
};

/**
 * Galaxy refuses a copy with no target history (the default handler); this story accepts one into
 * the source history, for the unit test's no-target success expectations.
 */
export const NoTargetCopiesIntoSource: Story = {
    decorators: [withCurrentHistory(RNA_SEQ)],
    parameters: { msw: { handlers: { copyContents: copyContents("copyIntoSource") } } },
};
