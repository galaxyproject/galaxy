/**
 * Unified API client for all Galaxy Pages (history-attached and standalone).
 * Uses the generated typed client against the /api/pages endpoints.
 */
import { type components, GalaxyApi } from "@/api";
import { rethrowSimple } from "@/utils/simple-error";

// --- Types (generated from the backend Page/PageRevision schemas) ---

export type HistoryPageSummary = components["schemas"]["PageSummary"];
export type HistoryPageDetails = components["schemas"]["PageDetails"];
export type PageRevisionSummary = components["schemas"]["PageRevisionSummary"];
export type PageRevisionDetails = components["schemas"]["PageRevisionDetails"];
export type CreateHistoryPagePayload = components["schemas"]["CreatePagePayload"];
export type UpdateHistoryPagePayload = components["schemas"]["UpdatePagePayload"];

// --- API functions ---

export async function fetchHistoryPages(historyId: string): Promise<HistoryPageSummary[]> {
    const { data, error } = await GalaxyApi().GET("/api/pages", {
        params: { query: { history_id: historyId, show_own: true, show_published: false } },
    });
    if (error) {
        rethrowSimple(error);
    }
    return data;
}

export async function fetchHistoryPage(pageId: string): Promise<HistoryPageDetails> {
    const { data, error } = await GalaxyApi().GET("/api/pages/{id}", {
        params: { path: { id: pageId } },
    });
    if (error) {
        rethrowSimple(error);
    }
    return data;
}

export async function createHistoryPage(payload: CreateHistoryPagePayload): Promise<HistoryPageDetails> {
    const { data, error } = await GalaxyApi().POST("/api/pages", { body: payload });
    if (error) {
        rethrowSimple(error);
    }
    return data;
}

export async function updateHistoryPage(
    pageId: string,
    payload: UpdateHistoryPagePayload,
): Promise<HistoryPageDetails> {
    const { data, error } = await GalaxyApi().PUT("/api/pages/{id}", {
        params: { path: { id: pageId } },
        body: payload,
    });
    if (error) {
        rethrowSimple(error);
    }
    return data;
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
    const { error } = await GalaxyApi().DELETE("/api/pages/{id}", {
        params: { path: { id: pageId } },
    });
    if (error) {
        rethrowSimple(error);
    }
}

export async function fetchPageRevisions(
    pageId: string,
    { sortDesc = false }: { sortDesc?: boolean } = {},
): Promise<PageRevisionSummary[]> {
    const { data, error } = await GalaxyApi().GET("/api/pages/{id}/revisions", {
        params: { path: { id: pageId }, query: { sort_desc: sortDesc } },
    });
    if (error) {
        rethrowSimple(error);
    }
    return data;
}

export async function fetchPageRevision(pageId: string, revisionId: string): Promise<PageRevisionDetails> {
    const { data, error } = await GalaxyApi().GET("/api/pages/{id}/revisions/{revision_id}", {
        params: { path: { id: pageId, revision_id: revisionId } },
    });
    if (error) {
        rethrowSimple(error);
    }
    return data;
}

export async function revertPageRevision(pageId: string, revisionId: string): Promise<PageRevisionDetails> {
    const { data, error } = await GalaxyApi().POST("/api/pages/{id}/revisions/{revision_id}/revert", {
        params: { path: { id: pageId, revision_id: revisionId } },
    });
    if (error) {
        rethrowSimple(error);
    }
    return data;
}
