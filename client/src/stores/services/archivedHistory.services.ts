import { fetcher, type components } from "@/schema";
import type { FetchArgType } from "openapi-typescript-fetch";

export type ArchivedHistorySummary = components["schemas"]["ArchivedHistorySummary"];
export type ArchivedHistoryDetailed = components["schemas"]["ArchivedHistoryDetailed"];
export type AsyncTaskResultSummary = components["schemas"]["AsyncTaskResultSummary"];

const _getArchivedHistories = fetcher.path("/api/histories/archived").method("get").create();
const _archiveHistory = fetcher.path("/api/histories/{history_id}/archive").method("post").create();
const _unarchiveHistory = fetcher.path("/api/histories/{history_id}/archive/restore").method("put").create();
const _reimportHistoryFromStoreAsync = fetcher.path("/api/histories/from_store_async").method("post").create();

type GetArchivedHistoriesParams = FetchArgType<typeof _getArchivedHistories>;
type SerializationOptions = Pick<GetArchivedHistoriesParams, "view" | "keys">;

interface FilterOptions {
    query?: string;
}

interface PaginationOptions {
    currentPage?: number;
    pageSize?: number;
}

interface SortingOptions {
    sortBy?: string;
    sortDesc?: boolean;
}

interface GetArchivedHistoriesOptions extends FilterOptions, PaginationOptions, SortingOptions, SerializationOptions {}

/**
 * Get a list of archived histories.
 */
export async function getArchivedHistories(
    options: GetArchivedHistoriesOptions = {}
): Promise<ArchivedHistorySummary[] | ArchivedHistoryDetailed[]> {
    const params = optionsToApiParams(options);
    const { data } = await _getArchivedHistories(params);
    if (params.view === "detailed") {
        return data as ArchivedHistoryDetailed[];
    }
    return data as ArchivedHistorySummary[];
}

/**
 * Archive a history.
 * @param historyId The history to archive
 * @param archiveExportId The optional archive export record to associate. This can be used to restore a snapshot copy of the history in the future.
 * @param purgeHistory Whether to purge the history after archiving. Can only be used in combination with an archive export record.
 * @returns The archived history summary.
 */
export async function archiveHistory(
    historyId: string,
    archiveExportId?: string,
    purgeHistory?: boolean
): Promise<ArchivedHistorySummary> {
    const { data } = await _archiveHistory({
        history_id: historyId,
        archive_export_id: archiveExportId,
        purge_history: purgeHistory,
    });
    return data as ArchivedHistorySummary;
}

/**
 * Unarchive/restore a history.
 * @param historyId The history to unarchive.
 * @param force Whether to force un-archiving for purged histories.
 * @returns The restored history summary.
 */
export async function unarchiveHistory(historyId: string, force?: boolean): Promise<ArchivedHistorySummary> {
    const { data } = await _unarchiveHistory({ history_id: historyId, force });
    return data as ArchivedHistorySummary;
}

/**
 * Reimport an archived history as a new copy from the associated export record.
 *
 * @param archivedHistory The archived history to reimport. It must have an associated export record.
 * @returns The async task result summary to track the reimport progress.
 */
export async function reimportHistoryFromExportRecordAsync(
    archivedHistory: ArchivedHistorySummary
): Promise<AsyncTaskResultSummary> {
    const { data } = await _reimportHistoryFromStoreAsync({
        model_store_format: archivedHistory.export_record_data?.model_store_format,
        store_content_uri: archivedHistory.export_record_data?.target_uri,
    });
    return data as AsyncTaskResultSummary;
}

function optionsToApiParams(options: GetArchivedHistoriesOptions): GetArchivedHistoriesParams {
    const params: GetArchivedHistoriesParams = {};
    if (options.query) {
        params.q = ["name-contains"];
        params.qv = [options.query];
    }
    params.offset = (options.currentPage ?? 0) * (options.pageSize ?? 10);
    params.limit = options.pageSize;
    params.order = options.sortBy ? `${options.sortBy}${options.sortDesc ? "-dsc" : "-asc"}` : undefined;
    params.view = options.view;
    params.keys = options.keys;
    return params;
}
