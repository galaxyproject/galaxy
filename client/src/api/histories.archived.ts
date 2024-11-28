import { type components, GalaxyApi, type GalaxyApiPaths } from "@/api";
import { rethrowSimple } from "@/utils/simple-error";

export type ArchivedHistorySummary = components["schemas"]["ArchivedHistorySummary"];
export type ArchivedHistoryDetailed = components["schemas"]["ArchivedHistoryDetailed"];
export type AnyArchivedHistory = ArchivedHistorySummary | ArchivedHistoryDetailed;

type MaybeArchivedHistoriesQueryParams = GalaxyApiPaths["/api/histories/archived"]["get"]["parameters"]["query"];
type ArchivedHistoriesQueryParams = Exclude<MaybeArchivedHistoriesQueryParams, undefined>;
type SerializationOptions = Pick<ArchivedHistoriesQueryParams, "view" | "keys">;

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
    histories: AnyArchivedHistory[];
    totalMatches: number;
}

const DEFAULT_PAGE_SIZE = 10;

/**
 * Get a list of archived histories.
 */
export async function fetchArchivedHistories(options: GetArchivedHistoriesOptions): Promise<ArchivedHistoriesResult> {
    const params = optionsToApiParams(options);

    const { response, data, error } = await GalaxyApi().GET("/api/histories/archived", {
        params: {
            query: params,
        },
    });

    if (error) {
        rethrowSimple(error);
    }

    const totalMatches = parseInt(response.headers.get("total_matches") ?? "0");
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

function optionsToApiParams(options: GetArchivedHistoriesOptions): ArchivedHistoriesQueryParams {
    const params: ArchivedHistoriesQueryParams = {};
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
