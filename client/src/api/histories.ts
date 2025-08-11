import type { AnyHistory, components, HistorySummary } from "@/api";
import { GalaxyApi } from "@/api";
import type { ArchivedHistorySummary } from "@/api/histories.archived";
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
