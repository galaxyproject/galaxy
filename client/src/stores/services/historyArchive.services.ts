import { fetcher, type components } from "@/schema";
import type { FetchArgType } from "openapi-typescript-fetch";

export type ArchivedHistorySummary = components["schemas"]["ArchivedHistorySummary"];
export type ArchivedHistoryDetailed = components["schemas"]["ArchivedHistoryDetailed"];
export type AsyncTaskResultSummary = components["schemas"]["AsyncTaskResultSummary"];

type GetArchivedHistoriesParams = FetchArgType<typeof getArchivedHistories>;
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

interface ArchivedHistoriesResult {
    histories: ArchivedHistorySummary[] | ArchivedHistoryDetailed[];
    totalMatches: number;
}

const DEFAULT_PAGE_SIZE = 10;

const getArchivedHistories = fetcher.path("/api/histories/archived").method("get").create();

/**
 * Get a list of archived histories.
 */
export async function fetchArchivedHistories(
    options: GetArchivedHistoriesOptions = {}
): Promise<ArchivedHistoriesResult> {
    const params = optionsToApiParams(options);
    const { data, headers } = await getArchivedHistories(params);
    const totalMatches = parseInt(headers.get("total_matches") ?? "0");
    if (params.view === "detailed") {
        return {
            histories: data as ArchivedHistoryDetailed[],
            totalMatches,
        };
    }
    return {
        histories: data as ArchivedHistorySummary[],
        totalMatches,
    };
}

const archiveHistory = fetcher.path("/api/histories/{history_id}/archive").method("post").create();

/**
 * Archive a history.
 * @param historyId The history to archive
 * @param archiveExportId The optional archive export record to associate. This can be used to restore a snapshot copy of the history in the future.
 * @param purgeHistory Whether to purge the history after archiving. Can only be used in combination with an archive export record.
 * @returns The archived history summary.
 */
export async function archiveHistoryById(
    historyId: string,
    archiveExportId?: string,
    purgeHistory?: boolean
): Promise<ArchivedHistorySummary> {
    const { data } = await archiveHistory({
        history_id: historyId,
        archive_export_id: archiveExportId,
        purge_history: purgeHistory,
    });
    return data as ArchivedHistorySummary;
}

const unarchiveHistory = fetcher
    .path("/api/histories/{history_id}/archive/restore")
    .method("put")
    // @ts-ignore: workaround for optional query parameters in PUT. More info here https://github.com/ajaishankar/openapi-typescript-fetch/pull/55
    .create({ force: undefined });

/**
 * Unarchive/restore a history.
 * @param historyId The history to unarchive.
 * @param force Whether to force un-archiving for purged histories.
 * @returns The restored history summary.
 */
export async function unarchiveHistoryById(historyId: string, force?: boolean): Promise<ArchivedHistorySummary> {
    const { data } = await unarchiveHistory({ history_id: historyId, force });
    return data as ArchivedHistorySummary;
}

const reimportHistoryFromStore = fetcher.path("/api/histories/from_store_async").method("post").create();

/**
 * Reimport an archived history as a new copy from the associated export record.
 *
 * @param archivedHistory The archived history to reimport. It must have an associated export record.
 * @returns The async task result summary to track the reimport progress.
 */
export async function reimportHistoryFromExportRecordAsync(
    archivedHistory: ArchivedHistorySummary
): Promise<AsyncTaskResultSummary> {
    if (!archivedHistory.export_record_data) {
        throw new Error("The archived history does not have an associated export record.");
    }
    const { data } = await reimportHistoryFromStore({
        model_store_format: archivedHistory.export_record_data.model_store_format,
        store_content_uri: archivedHistory.export_record_data.target_uri,
    });
    return data as AsyncTaskResultSummary;
}

function optionsToApiParams(options: GetArchivedHistoriesOptions): GetArchivedHistoriesParams {
    const params: GetArchivedHistoriesParams = {};
    if (options.query) {
        params.q = ["name-contains"];
        params.qv = [options.query];
    }
    const pageSize = options.pageSize ?? DEFAULT_PAGE_SIZE;
    params.offset = (options.currentPage ? options.currentPage - 1 : 0) * pageSize;
    params.limit = pageSize;
    params.order = options.sortBy ? `${options.sortBy}${options.sortDesc ? "-dsc" : "-asc"}` : undefined;
    params.view = options.view;
    params.keys = options.keys;
    return params;
}
