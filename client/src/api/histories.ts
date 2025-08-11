import type { AnyHistory, components, HistorySummary } from "@/api";
import type { ArchivedHistorySummary } from "@/api/histories.archived";

type HistoryDetailed = components["schemas"]["HistoryDetailed"];

export type HistoryContentsResult = components["schemas"]["HistoryContentsResult"];

export type UpdateHistoryPayload = components["schemas"]["UpdateHistoryPayload"];

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
