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

export type MyHistory = HistorySummary & {
    username: string;
};

export type SharedHistory = MyHistory & {
    owner: string;
};

export type PublishedHistory = SharedHistory & {
    published: boolean;
};

export type AnyHistoryEntry = MyHistory | SharedHistory | PublishedHistory | ArchivedHistorySummary;

export interface GetHistoriesOptions {
    limit: number;
    offset: number;
    search: string;
    sortBy: HistorySortByLiteral;
    sortDesc: boolean;
}

export function currentUserOwnsHistory(username: string) {
    const userStore = useUserStore();
    return userStore.matchesCurrentUsername(username);
}

export function isMyHistory(history: AnyHistoryEntry): history is MyHistory {
    return "username" in history && currentUserOwnsHistory(history.username);
}

export function isSharedHistory(history: AnyHistoryEntry): history is SharedHistory {
    return "username" in history && !currentUserOwnsHistory(history.username);
}

export function isPublishedHistory(history: AnyHistoryEntry): history is PublishedHistory {
    return "published" in history && history.published;
}

export function isArchivedHistory(history: AnyHistoryEntry): history is ArchivedHistorySummary {
    return "archived" in history && history.archived;
}

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

export async function getSharedHistories(
    options?: GetHistoriesOptions
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

export async function getPublishedHistories(
    options?: GetHistoriesOptions
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

export async function getArchivedHistories(
    options?: GetHistoriesOptions
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
