import type { components } from "@/api";
import { GalaxyApi } from "@/api";
import { rethrowSimple } from "@/utils/simple-error";

export type HistoryNotebookSummary = components["schemas"]["HistoryNotebookSummary"];
export type HistoryNotebookDetails = components["schemas"]["HistoryNotebookDetails"];
export type HistoryNotebookRevisionSummary = components["schemas"]["HistoryNotebookRevisionSummary"];
export type HistoryNotebookRevisionDetails = components["schemas"]["HistoryNotebookRevisionDetails"];
export type CreateNotebookPayload = components["schemas"]["CreateHistoryNotebookPayload"];
export type UpdateNotebookPayload = components["schemas"]["UpdateHistoryNotebookPayload"];

export async function fetchHistoryNotebooks(historyId: string): Promise<HistoryNotebookSummary[]> {
    const { data, error } = await GalaxyApi().GET("/api/histories/{history_id}/notebooks", {
        params: { path: { history_id: historyId } },
    });
    if (error) {
        rethrowSimple(error);
    }
    return data;
}

export async function fetchHistoryNotebook(historyId: string, notebookId: string): Promise<HistoryNotebookDetails> {
    const { data, error } = await GalaxyApi().GET("/api/histories/{history_id}/notebooks/{notebook_id}", {
        params: { path: { history_id: historyId, notebook_id: notebookId } },
    });
    if (error) {
        rethrowSimple(error);
    }
    return data;
}

export async function createHistoryNotebook(
    historyId: string,
    payload: CreateNotebookPayload,
): Promise<HistoryNotebookDetails> {
    const { data, error } = await GalaxyApi().POST("/api/histories/{history_id}/notebooks", {
        params: { path: { history_id: historyId } },
        body: payload,
    });
    if (error) {
        rethrowSimple(error);
    }
    return data;
}

export async function updateHistoryNotebook(
    historyId: string,
    notebookId: string,
    payload: UpdateNotebookPayload,
): Promise<HistoryNotebookDetails> {
    const { data, error } = await GalaxyApi().PUT("/api/histories/{history_id}/notebooks/{notebook_id}", {
        params: { path: { history_id: historyId, notebook_id: notebookId } },
        body: payload,
    });
    if (error) {
        rethrowSimple(error);
    }
    return data;
}

export async function deleteHistoryNotebook(historyId: string, notebookId: string): Promise<void> {
    const { error } = await GalaxyApi().DELETE("/api/histories/{history_id}/notebooks/{notebook_id}", {
        params: { path: { history_id: historyId, notebook_id: notebookId } },
    });
    if (error) {
        rethrowSimple(error);
    }
}

export async function fetchNotebookRevisions(
    historyId: string,
    notebookId: string,
): Promise<HistoryNotebookRevisionSummary[]> {
    const { data, error } = await GalaxyApi().GET("/api/histories/{history_id}/notebooks/{notebook_id}/revisions", {
        params: { path: { history_id: historyId, notebook_id: notebookId } },
    });
    if (error) {
        rethrowSimple(error);
    }
    return data;
}

export async function fetchNotebookRevision(
    historyId: string,
    notebookId: string,
    revisionId: string,
): Promise<HistoryNotebookRevisionDetails> {
    const { data, error } = await GalaxyApi().GET(
        "/api/histories/{history_id}/notebooks/{notebook_id}/revisions/{revision_id}",
        {
            params: { path: { history_id: historyId, notebook_id: notebookId, revision_id: revisionId } },
        },
    );
    if (error) {
        rethrowSimple(error);
    }
    return data;
}

export async function revertNotebookRevision(
    historyId: string,
    notebookId: string,
    revisionId: string,
): Promise<HistoryNotebookDetails> {
    const { data, error } = await GalaxyApi().POST(
        "/api/histories/{history_id}/notebooks/{notebook_id}/revisions/{revision_id}/revert",
        {
            params: { path: { history_id: historyId, notebook_id: notebookId, revision_id: revisionId } },
        },
    );
    if (error) {
        rethrowSimple(error);
    }
    return data;
}
