/**
 * Unified API client for all Galaxy Pages (history-attached and standalone).
 * Uses /api/pages endpoints.
 */
import axios from "axios";

import { withPrefix } from "@/utils/redirect";
import { rethrowSimple } from "@/utils/simple-error";

// --- Types matching backend Page/PageRevision schemas ---

export interface HistoryPageSummary {
    id: string;
    title: string;
    slug: string | null;
    history_id: string | null;
    source_invocation_id: string | null;
    published: boolean;
    importable: boolean;
    deleted: boolean;
    latest_revision_id: string;
    revision_ids: string[];
    create_time: string;
    update_time: string;
    username: string;
    email_hash: string;
    author_deleted: boolean;
    model_class: "Page";
    tags: string[];
}

export interface HistoryPageDetails extends HistoryPageSummary {
    content: string | null;
    content_editor: string | null;
    content_format: "markdown" | "html";
    edit_source: string | null;
    annotation: string | null;
}

export interface PageRevisionSummary {
    id: string;
    page_id: string;
    edit_source: string | null;
    create_time: string;
    update_time: string;
}

export interface PageRevisionDetails extends PageRevisionSummary {
    title: string | null;
    content: string | null;
    content_format: string | null;
}

export interface CreateHistoryPagePayload {
    title: string;
    history_id: string;
    content?: string | null;
    content_format?: string;
}

export interface UpdateHistoryPagePayload {
    title?: string;
    content?: string;
    content_format?: string;
    edit_source?: string;
}

// --- API functions ---

export async function fetchHistoryPages(historyId: string): Promise<HistoryPageSummary[]> {
    try {
        const { data } = await axios.get(withPrefix(`/api/pages`), {
            params: { history_id: historyId, show_own: true, show_published: false },
        });
        return data;
    } catch (e) {
        rethrowSimple(e);
        throw e; // unreachable, makes TS happy
    }
}

export async function fetchHistoryPage(pageId: string): Promise<HistoryPageDetails> {
    try {
        const { data } = await axios.get(withPrefix(`/api/pages/${pageId}`));
        return data;
    } catch (e) {
        rethrowSimple(e);
        throw e;
    }
}

export async function createHistoryPage(payload: CreateHistoryPagePayload): Promise<HistoryPageDetails> {
    try {
        const { data } = await axios.post(withPrefix("/api/pages"), payload);
        return data;
    } catch (e) {
        rethrowSimple(e);
        throw e;
    }
}

export async function updateHistoryPage(
    pageId: string,
    payload: UpdateHistoryPagePayload,
): Promise<HistoryPageDetails> {
    try {
        const { data } = await axios.put(withPrefix(`/api/pages/${pageId}`), payload);
        return data;
    } catch (e) {
        rethrowSimple(e);
        throw e;
    }
}

/** Save page content via PUT (replaces legacy POST /revisions save). */
export async function savePage(
    pageId: string,
    content: string,
    editSource: string = "user",
): Promise<HistoryPageDetails> {
    return updateHistoryPage(pageId, { content, edit_source: editSource });
}

export async function deleteHistoryPage(pageId: string): Promise<void> {
    try {
        await axios.delete(withPrefix(`/api/pages/${pageId}`));
    } catch (e) {
        rethrowSimple(e);
        throw e;
    }
}

export async function fetchPageRevisions(
    pageId: string,
    { sortDesc = false }: { sortDesc?: boolean } = {},
): Promise<PageRevisionSummary[]> {
    try {
        const { data } = await axios.get(withPrefix(`/api/pages/${pageId}/revisions`), {
            params: { sort_desc: sortDesc },
        });
        return data;
    } catch (e) {
        rethrowSimple(e);
        throw e;
    }
}

export async function fetchPageRevision(pageId: string, revisionId: string): Promise<PageRevisionDetails> {
    try {
        const { data } = await axios.get(withPrefix(`/api/pages/${pageId}/revisions/${revisionId}`));
        return data;
    } catch (e) {
        rethrowSimple(e);
        throw e;
    }
}

export async function revertPageRevision(pageId: string, revisionId: string): Promise<PageRevisionDetails> {
    try {
        const { data } = await axios.post(withPrefix(`/api/pages/${pageId}/revisions/${revisionId}/revert`));
        return data;
    } catch (e) {
        rethrowSimple(e);
        throw e;
    }
}
