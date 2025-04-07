import { type AnyHistory, type components } from "@/api";

type HistoryDetailed = components["schemas"]["HistoryDetailed"];

export type HistoryContentsResult = components["schemas"]["HistoryContentsResult"];

export function hasImportable(entry?: AnyHistory): entry is HistoryDetailed {
    return entry !== undefined && "importable" in entry;
}
