import type { AnyHistory, components, HistorySortByLiteral, HistorySummary } from "@/api";
import { GalaxyApi } from "@/api";
import type { ArchivedHistorySummary } from "@/api/histories.archived";
import { useUserStore } from "@/stores/userStore";
import { rethrowSimple } from "@/utils/simple-error";

type HistoryDetailed = components["schemas"]["HistoryDetailed"];

export type HistoryContentsResult = components["schemas"]["HistoryContentsResult"];

export type UpdateHistoryPayload = components["schemas"]["UpdateHistoryPayload"];

export type CustomHistoryView = components["schemas"]["CustomHistoryView"];

export type HistoryCounts = Pick<CustomHistoryView, "nice_size" | "contents_active" | "contents_states">;

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

/**
 * Fetches the current user's history entries.
 * @param {GetHistoriesOptions} options The options for fetching histories
 * @returns {Promise<{ data: MyHistory[]; total: number }>} A promise that resolves to the user's history entries
 */
export async function getMyHistories(options?: GetHistoriesOptions): Promise<{ data: MyHistory[]; total: number }> {
    const { limit = 24, offset = 0, search = "", sortBy = "update_time", sortDesc = false } = options || {};

    const { response, data, error } = await GalaxyApi().GET("/api/histories", {
        params: {
            query: {
                view: "summary",
                keys: "username",
                limit: limit,
                offset: offset,
                search: search,
                sort_by: sortBy,
                sort_desc: sortDesc,
                show_own: true,
                show_published: false,
                show_shared: false,
                show_archived: false,
            },
        },
    });

    if (error) {
        rethrowSimple(error);
    }

    return { data: data as MyHistory[], total: parseInt(response.headers.get("total_matches") ?? "0") };
}

/**
 * Fetches the current user's shared history entries.
 * @param {GetHistoriesOptions} options The options for fetching histories
 * @returns {Promise<{ data: SharedHistory[]; total: number }>} A promise that resolves to the shared history entries
 */
export async function getSharedHistories(
    options?: GetHistoriesOptions,
): Promise<{ data: SharedHistory[]; total: number }> {
    const { limit = 24, offset = 0, search = "", sortBy = "update_time", sortDesc = false } = options || {};

    const { response, data, error } = await GalaxyApi().GET("/api/histories", {
        params: {
            query: {
                view: "summary",
                keys: "username,owner",
                limit: limit,
                offset: offset,
                search: search,
                sort_by: sortBy,
                sort_desc: sortDesc,
                show_own: false,
                show_published: false,
                show_shared: true,
                show_archived: false,
            },
        },
    });

    if (error) {
        rethrowSimple(error);
    }

    return { data: data as SharedHistory[], total: parseInt(response.headers.get("total_matches") ?? "0") };
}

/**
 * Fetches the published history entries.
 * @param {GetHistoriesOptions} options The options for fetching histories
 * @returns {Promise<{ data: PublishedHistory[]; total: number }>} A promise that resolves to the published history entries
 */
export async function getPublishedHistories(
    options?: GetHistoriesOptions,
): Promise<{ data: PublishedHistory[]; total: number }> {
    const { limit = 24, offset = 0, search = "", sortBy = "update_time", sortDesc = false } = options || {};

    const { response, data, error } = await GalaxyApi().GET("/api/histories", {
        params: {
            query: {
                view: "summary",
                keys: "username,owner,published",
                limit: limit,
                offset: offset,
                search: search,
                sort_by: sortBy,
                sort_desc: sortDesc,
                show_own: false,
                show_published: true,
                show_shared: false,
                show_archived: false,
            },
        },
    });

    if (error) {
        rethrowSimple(error);
    }

    return { data: data as PublishedHistory[], total: parseInt(response.headers.get("total_matches") ?? "0") };
}

/**
 * Fetches the current user's archived history entries.
 * @param {GetHistoriesOptions} options The options for fetching histories
 * @returns {Promise<{ data: ArchivedHistorySummary[]; total: number }>} A promise that resolves to the archived history entries
 */
export async function getArchivedHistories(
    options?: GetHistoriesOptions,
): Promise<{ data: ArchivedHistorySummary[]; total: number }> {
    const { limit = 24, offset = 0, search = "", sortBy = "update_time", sortDesc = false } = options || {};

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
