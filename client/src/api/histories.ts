import type { AnyHistory, components, HistorySortByLiteral, HistorySummary } from "@/api";
import { GalaxyApi } from "@/api";
import type { ArchivedHistorySummary } from "@/api/histories.archived";
import { useUserStore } from "@/stores/userStore";
import { rethrowSimple } from "@/utils/simple-error";

type HistoryDetailed = components["schemas"]["HistoryDetailed"];

export type HistoryContentsResult = components["schemas"]["HistoryContentsResult"];

export type UpdateHistoryPayload = components["schemas"]["UpdateHistoryPayload"];

export type CustomHistoryView = components["schemas"]["CustomHistoryView"];

export type WorkflowExtractionByIdsPayload = components["schemas"]["WorkflowExtractionByIdsPayload"];
export type WorkflowExtractionJob = components["schemas"]["WorkflowExtractionJob"];
type WorkflowExtractionResult = components["schemas"]["WorkflowExtractionResult"];
export type WorkflowExtractionSummary = components["schemas"]["WorkflowExtractionSummary"];
export type OutputLabelHint = components["schemas"]["OutputLabelHint"];

export type HistoryCounts = Pick<CustomHistoryView, "nice_size" | "contents_active" | "contents_states">;

export type BeaconHistory = Required<Pick<CustomHistoryView, "id" | "contents_active" | "create_time">>;

export function hasImportable(entry?: AnyHistory): entry is HistoryDetailed {
    return entry !== undefined && "importable" in entry;
}

/**
 * Represents a history entry owned by the current user.
 */
export type MyHistory = HistorySummary & {
    username: string;
};

/**
 * Represents a history entry shared with the current user.
 */
export type SharedHistory = MyHistory & {
    owner: string;
};

/**
 * Represents a history entry published.
 */
export type PublishedHistory = SharedHistory & {
    published: boolean;
};

/**
 * Represents any history entry.
 */
export type AnyHistoryEntry = MyHistory | SharedHistory | PublishedHistory | ArchivedHistorySummary;

/**
 * Represents a reference to a history, containing only the fields necessary for identifying a history in API calls.
 */
export type HistoryReference = Pick<HistorySummary, "id" | "model_class">;

/**
 * Represents the options for fetching histories.
 */
export interface GetHistoriesOptions {
    limit: number;
    offset: number;
    search: string;
    sortBy: HistorySortByLiteral;
    sortDesc: boolean;
}

/**
 * Represents the visibility flags accepted by the histories index endpoint.
 *
 * The backend defaults `show_published` to `true`, so every request built here
 * passes an explicit value for each flag. Otherwise a listing of the user's own
 * histories would silently include other users' published histories.
 */
export interface HistoryVisibilityOptions {
    showOwn?: boolean;
    showPublished?: boolean;
    showShared?: boolean;
    showArchived?: boolean;
}

/**
 * Represents the options for fetching histories from the index endpoint,
 * including the visibility flags and the serialization keys to request.
 */
export interface GetHistoryListOptions extends Partial<GetHistoriesOptions>, HistoryVisibilityOptions {
    /** Additional serialization keys requested on top of the `summary` view. */
    keys?: string;
}

/**
 * Represents a page of history entries together with the total number of matches.
 */
export interface HistoryListResult<T> {
    data: T[];
    total: number;
}

const DEFAULT_HISTORY_LIMIT = 24;

/**
 * Checks if the current user owns a history entry.
 * @param {string} username The username of the history owner
 * @returns True if the current user owns the history, false otherwise
 */
export function currentUserOwnsHistory(username: string) {
    const userStore = useUserStore();
    return userStore.matchesCurrentUsername(username);
}

/**
 * Checks if a history entry is owned by the current user.
 * @param {AnyHistoryEntry} history The history entry to check ownership of and its type
 * @returns True if the current user is the owner of the history and its type is MyHistory, false otherwise
 */
export function isMyHistory(history: AnyHistoryEntry): history is MyHistory {
    return "username" in history && currentUserOwnsHistory(history.username);
}

/**
 * Checks if a history entry is owned by the current user.
 * @param {AnyHistoryEntry} history The history entry to check ownership of and its type
 * @returns True if the current user is not the owner of the history and its type is SharedHistory, false otherwise
 */
export function isSharedHistory(history: AnyHistoryEntry): history is SharedHistory {
    return "username" in history && !currentUserOwnsHistory(history.username);
}

/**
 * Checks if a history entry is published.
 * @param {AnyHistoryEntry} history The history entry to check
 * @returns True if the history is published and its type is PublishedHistory, false otherwise
 */
export function isPublishedHistory(history: AnyHistoryEntry): history is PublishedHistory {
    return "published" in history && history.published;
}

/**
 * Checks if a history entry is archived.
 * @param {AnyHistoryEntry} history The history entry to check
 * @returns True if the history is archived and its type is ArchivedHistorySummary, false otherwise
 */
export function isArchivedHistory(history: AnyHistoryEntry): history is ArchivedHistorySummary {
    return "archived" in history && history.archived;
}

// TODO: Need to polish this and also use this in the history store
//       (why are the `all_datasets` and `archive_type` parameters required?)
export async function createNewHistory(name?: string): Promise<HistoryDetailed> {
    const { data, error } = await GalaxyApi().POST("/api/histories", {
        body: { all_datasets: true, archive_type: "url", name },
    });

    if (error) {
        rethrowSimple(error);
    }

    // TODO: Is it really returning a HistoryDetailed?
    return data as HistoryDetailed;
}

/**
 * Fetches the beacon histories for the current user.
 * @param beaconHistoryName The beacon history name filter to apply when fetching.
 * @returns A promise that resolves to the beacon histories
 */
export async function getBeaconHistories(beaconHistoryName: string): Promise<BeaconHistory[]> {
    const { data, error } = await GalaxyApi().GET("/api/histories", {
        params: {
            query: {
                keys: "id,contents_active,create_time",
                q: ["name"],
                qv: [beaconHistoryName],
            },
        },
    });

    if (error) {
        rethrowSimple(error);
    }

    return data as BeaconHistory[];
}

/**
 * Fetches history entries from the histories index endpoint.
 *
 * All visibility flags are optional and default to a listing of the current
 * user's own, non-archived histories. They are always sent explicitly, so a
 * listing can never pick up the backend's `show_published=true` default.
 *
 * @param {GetHistoryListOptions} options The options for fetching histories
 * @returns {Promise<HistoryListResult<T>>} A promise that resolves to the matching history entries
 */
export async function getHistories<T = AnyHistoryEntry>(
    options?: GetHistoryListOptions,
): Promise<HistoryListResult<T>> {
    const {
        limit = DEFAULT_HISTORY_LIMIT,
        offset = 0,
        search = "",
        sortBy = "update_time",
        sortDesc = false,
        showOwn = true,
        showPublished = false,
        showShared = false,
        showArchived = false,
        keys = "username",
    } = options || {};

    const { response, data, error } = await GalaxyApi().GET("/api/histories", {
        params: {
            query: {
                view: "summary",
                keys: keys,
                limit: limit,
                offset: offset,
                search: search,
                sort_by: sortBy,
                sort_desc: sortDesc,
                show_own: showOwn,
                show_published: showPublished,
                show_shared: showShared,
                show_archived: showArchived,
            },
        },
    });

    if (error) {
        rethrowSimple(error);
    }

    return { data: data as T[], total: parseInt(response.headers.get("total_matches") ?? "0") };
}

/**
 * Fetches the current user's history entries.
 * @param {Partial<GetHistoriesOptions>} options The options for fetching histories
 * @returns {Promise<HistoryListResult<MyHistory>>} A promise that resolves to the user's history entries
 */
export function getMyHistories(options?: Partial<GetHistoriesOptions>): Promise<HistoryListResult<MyHistory>> {
    return getHistories<MyHistory>({
        ...options,
        keys: "username",
        showOwn: true,
        showPublished: false,
        showShared: false,
        showArchived: false,
    });
}

/**
 * Fetches the current user's shared history entries.
 * @param {Partial<GetHistoriesOptions>} options The options for fetching histories
 * @returns {Promise<HistoryListResult<SharedHistory>>} A promise that resolves to the shared history entries
 */
export function getSharedHistories(options?: Partial<GetHistoriesOptions>): Promise<HistoryListResult<SharedHistory>> {
    return getHistories<SharedHistory>({
        ...options,
        keys: "username,owner",
        showOwn: false,
        showPublished: false,
        showShared: true,
        showArchived: false,
    });
}

/**
 * Fetches the published history entries.
 * @param {Partial<GetHistoriesOptions>} options The options for fetching histories
 * @returns {Promise<HistoryListResult<PublishedHistory>>} A promise that resolves to the published history entries
 */
export function getPublishedHistories(
    options?: Partial<GetHistoriesOptions>,
): Promise<HistoryListResult<PublishedHistory>> {
    return getHistories<PublishedHistory>({
        ...options,
        keys: "username,owner,published",
        showOwn: false,
        showPublished: true,
        showShared: false,
        showArchived: false,
    });
}

/**
 * Fetches the current user's archived history entries.
 *
 * Archived histories have their own endpoint (which implies the visibility
 * flags), so this wrapper does not go through `getHistories`.
 *
 * @param {Partial<GetHistoriesOptions>} options The options for fetching histories
 * @returns {Promise<HistoryListResult<ArchivedHistorySummary>>} A promise that resolves to the archived history entries
 */
export async function getArchivedHistories(
    options?: Partial<GetHistoriesOptions>,
): Promise<HistoryListResult<ArchivedHistorySummary>> {
    const {
        limit = DEFAULT_HISTORY_LIMIT,
        offset = 0,
        search = "",
        sortBy = "update_time",
        sortDesc = false,
    } = options || {};

    const { response, data, error } = await GalaxyApi().GET("/api/histories/archived", {
        params: {
            query: {
                view: "summary",
                limit: limit,
                offset: offset,
                search: search,
                sort_by: sortBy,
                sort_desc: sortDesc,
            },
        },
    });

    if (error) {
        rethrowSimple(error);
    }

    return { data: data as ArchivedHistorySummary[], total: parseInt(response.headers.get("total_matches") ?? "0") };
}

/**
 * Fetches the history counts for a specific history entry.
 * @param {string} historyId The ID of the history entry to fetch counts for
 * @returns {Promise<HistoryCounts>} A promise that resolves to the history counts
 */
export async function getHistoryCounts(historyId: string): Promise<HistoryCounts> {
    const { data, error } = await GalaxyApi().GET("/api/histories/{history_id}", {
        params: {
            path: { history_id: historyId },
            query: {
                keys: "nice_size,contents_active,contents_states",
            },
        },
    });

    if (error) {
        rethrowSimple(error);
    }

    return data as HistoryCounts;
}

export type StorageOperationMode = components["schemas"]["StorageOperationMode"];
export type StorageOperationExecutePolicy = components["schemas"]["StorageOperationExecutePolicy"];
export type StorageOperationPreviewResponse = components["schemas"]["StorageOperationPreviewResponse"];
export type StorageOperationExecuteResponse = components["schemas"]["StorageOperationExecuteResponse"];
export type StorageOperationRunResponse = components["schemas"]["StorageOperationRunResponse"];
export type StorageOperationRunItemStatus = components["schemas"]["StorageOperationRunItemStatus"];

export interface StorageOperationRunItemsOptions {
    offset?: number;
    limit?: number;
    search?: string;
}

export interface StorageOperationRunItemsWithTotal {
    data: StorageOperationRunItemStatus[];
    totalMatches: number | null;
}

export async function getStorageOperationRunStatus(
    history: HistoryReference,
    runId: string,
): Promise<StorageOperationRunResponse> {
    const { data, error } = await GalaxyApi().GET("/api/histories/{history_id}/contents/bulk/storage/runs/{run_id}", {
        params: {
            path: { history_id: history.id, run_id: runId },
        },
    });

    if (error) {
        rethrowSimple(error);
    }

    return data;
}

export async function getStorageOperationRunItemsWithTotal(
    history: HistoryReference,
    runId: string,
    options: StorageOperationRunItemsOptions = {},
): Promise<StorageOperationRunItemsWithTotal> {
    const { offset = 0, limit = 50, search } = options;
    const { response, data, error } = await GalaxyApi().GET(
        "/api/histories/{history_id}/contents/bulk/storage/runs/{run_id}/items",
        {
            params: {
                path: { history_id: history.id, run_id: runId },
                query: {
                    offset,
                    limit,
                    search,
                },
            },
        },
    );

    if (error) {
        rethrowSimple(error);
    }

    const totalMatchesHeader = response.headers.get("total_matches");
    const totalMatches = totalMatchesHeader !== null ? parseInt(totalMatchesHeader, 10) : null;
    return {
        data,
        totalMatches: Number.isNaN(totalMatches) ? null : totalMatches,
    };
}

/**
 * Fetches the workflow extraction summary for a specific history entry.
 * @param {string} historyId The ID of the history entry to fetch the workflow extraction summary for
 * @returns {Promise<WorkflowExtractionSummary>} A promise that resolves to the workflow extraction summary
 */
export async function extractWorkflowFromHistory(historyId: string): Promise<WorkflowExtractionSummary> {
    const { data, error } = await GalaxyApi().GET("/api/histories/{history_id}/extraction_summary", {
        params: {
            path: { history_id: historyId },
        },
    });

    if (error) {
        rethrowSimple(error);
    }

    return data as WorkflowExtractionSummary;
}

export async function extractWorkflowByIds(payload: WorkflowExtractionByIdsPayload): Promise<WorkflowExtractionResult> {
    const { data, error } = await GalaxyApi().POST("/api/workflows/extract", {
        body: payload,
    });

    if (error) {
        rethrowSimple(error);
    }

    return data as WorkflowExtractionResult;
}
