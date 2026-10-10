import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { withCurrentHistory } from "@tests/test-data/currentHistory";

import type { HistorySummary } from "@/api";
import { http } from "@/api/client/__mocks__/http";

import { DELETED_HISTORY, EMPTY_HISTORY, HISTORY_CONTENTS, RNA_SEQ, VARIANT_CALLING } from "./test_fixtures";

import DatasetCopy from "./DatasetCopy.vue";

/** Lists the user's histories, as `/api/histories` does: deleted ones are left out. */
function historyList(histories: HistorySummary[]) {
    return http.get("/api/histories", ({ response }) => response(200).json(histories.filter((h) => !h.deleted)));
}

/** Answers each history's contents from `HISTORY_CONTENTS`. */
const historyContents = http.get("/api/histories/{history_id}/contents", ({ params, response }) =>
    response(200).json(HISTORY_CONTENTS[params.history_id] ?? []),
);

/**
 * Copies as Galaxy does: into the named new history, or else the chosen ones. With neither, Galaxy
 * refuses, unless `withoutTarget` says to copy into the source history.
 */
function copyContents(withoutTarget: "refuse" | "copyIntoSource" = "refuse") {
    return http.post("/api/histories/{history_id}/copy_contents", async ({ params, request, response }) => {
        const { target_history_ids, target_history_name } = await request.json();
        if (target_history_name) {
            return response(200).json({ history_ids: ["2c7f9e4b1a8d0365"] });
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

/**
 * The current history, listed first, is the source: two reads and the pair built from them. Copying
 * with no target history chosen gets Galaxy's refusal.
 */
export const CopyFromCurrentHistory: Story = { decorators: [withCurrentHistory(RNA_SEQ)] };

/** The current history is the source wherever it sits in the list. */
export const CurrentHistoryListedSecond: Story = { decorators: [withCurrentHistory(VARIANT_CALLING)] };

/** A deleted current history isn't listed, so the first listed history is the source. */
export const CurrentHistoryNotListed: Story = { decorators: [withCurrentHistory(DELETED_HISTORY)] };

/** Without a current history, the first listed history is the source. */
export const NoCurrentHistory: Story = {};

/** The current history has nothing to copy yet. */
export const EmptyCurrentHistory: Story = {
    decorators: [withCurrentHistory(EMPTY_HISTORY)],
    parameters: { msw: { handlers: { histories: historyList([EMPTY_HISTORY, RNA_SEQ]) } } },
};

/**
 * Galaxy refuses a copy with no target history (the default handler); this story accepts one into
 * the source history, for the unit test's no-target success expectations.
 */
export const NoTargetCopiesIntoSource: Story = {
    decorators: [withCurrentHistory(RNA_SEQ)],
    parameters: { msw: { handlers: { copyContents: copyContents("copyIntoSource") } } },
};
