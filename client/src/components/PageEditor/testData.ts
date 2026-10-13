import { getFakeHistorySummaryExtended } from "@tests/test-data";
import { getFakePageRevisionDetails, getFakePageSummary } from "@tests/test-data/pages";

import type { HistorySummaryExtended } from "@/api";
import { http } from "@/api/client/__mocks__/http";

const NOTEBOOK_HISTORY_ID = "history-1";

export const FAKE_PAGE_SUMMARY = getFakePageSummary({
    id: "page-1",
    history_id: NOTEBOOK_HISTORY_ID,
    title: "My Analysis",
    latest_revision_id: "rev-1",
    revision_ids: ["rev-1"],
});

export const FAKE_PAGE_UNTITLED = getFakePageSummary({
    ...FAKE_PAGE_SUMMARY,
    id: "page-2",
    title: "",
});

/** The history the notebooks above belong to, owned by the default signed-in user (`fake_user_id`). */
export const NOTEBOOK_HISTORY = getFakeHistorySummaryExtended({
    id: NOTEBOOK_HISTORY_ID,
    name: "Paired-end RNA-seq",
});

/** The same history as another user's, shared with the signed-in user. */
export const OTHER_USERS_NOTEBOOK_HISTORY = getFakeHistorySummaryExtended({
    ...NOTEBOOK_HISTORY,
    user_id: "other_user_id",
});

/** Answers the history the history store loads by id, as `/api/histories/{id}` does with the store's keys. */
export function notebookHistory(history: HistorySummaryExtended) {
    return http.get("/api/histories/{history_id}", ({ response }) => response(200).json(history));
}

export const FAKE_PAGE_REVISION = getFakePageRevisionDetails({
    id: "rev-1",
    page_id: "page-1",
    title: "My Analysis",
    content: "# Analysis report\nReads processed: 12000\nReference build: hg19",
    content_editor: "# Analysis report\nReads processed: 12000\nReference build: hg19",
});

export const PAGE_CURRENT_CONTENT =
    "# Analysis report\nReads processed: 16000\nReference build: hg38\nAligner: Bowtie2";
export const PAGE_PREVIOUS_CONTENT = "# Analysis report\nReads processed: 8000";

export const PAGE_ORIGINAL_SECTIONS =
    "# Intro\nAnalysis of paired-end RNA-seq reads.\n# Methods\nReads aligned with STAR.\n# Results\nExpression counts pending.";
export const PAGE_PROPOSED_SECTIONS =
    "# Intro\nAnalysis of paired-end RNA-seq reads after adapter trimming.\n# Methods\nReads aligned with STAR.\n# Results\nExpression counts ready.";
