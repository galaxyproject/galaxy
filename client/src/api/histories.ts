import type { AnyHistory, components } from "@/api";

type HistoryDetailed = components["schemas"]["HistoryDetailed"];

export type HistoryContentsResult = components["schemas"]["HistoryContentsResult"];

export type UpdateHistoryPayload = components["schemas"]["UpdateHistoryPayload"];

export function hasImportable(entry?: AnyHistory): entry is HistoryDetailed {
    return entry !== undefined && "importable" in entry;
}
