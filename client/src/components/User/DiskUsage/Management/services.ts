import { getAppRoot } from "@/onload/loadConfig";
import { rethrowSimple } from "@/utils/simple-error";
import axios from "axios";
import {
    CleanableSummary,
    CleanupResult,
    type CleanableItem,
    type CleanupResultResponse,
    type ItemError,
    type PaginationOptions,
} from "./Cleanup/model";

const datasetKeys = "id,name,size,update_time,hda_ldda";
const isDataset = "q=history_content_type-eq&qv=dataset";
const isDeleted = "q=deleted-eq&qv=True";
const isNotPurged = "q=purged-eq&qv=False";
const maxItemsToFetch = 500;
const discardedDatasetsQueryParams = `${isDataset}&${isDeleted}&${isNotPurged}&limit=${maxItemsToFetch}`;

const historyKeys = "id,name,size,update_time";
const discardedHistoriesQueryParams = `&${isDeleted}&${isNotPurged}&limit=${maxItemsToFetch}`;

interface DiscardedDataset extends CleanableItem {
    hda_ldda: string;
}

interface DatasetSourceId {
    id: string;
    src: string;
}

interface DatasetErrorMessage {
    dataset: DatasetSourceId;
    error_message: string;
}

interface DeleteDatasetBatchResult {
    success_count: number;
    errors?: DatasetErrorMessage[];
}

type DiscardedHistory = CleanableItem;

/**
 * Calculates the total amount of bytes that can be cleaned by permanently removing
 * deleted datasets.
 * @returns Object containing information about how much can be cleaned.
 */
export async function fetchDiscardedDatasetsSummary(): Promise<CleanableSummary> {
    //TODO: possible optimization -> moving this to specific API endpoint so we don't have to parse
    //      potentially a huge number of items
    const summaryKeys = "size";
    const url = `${getAppRoot()}api/datasets?keys=${summaryKeys}&${discardedDatasetsQueryParams}`;
    try {
        const { data } = await axios.get(url);
        const totalSizeInBytes = data.reduce(
            (partial_sum: number, item: DiscardedDataset) => partial_sum + item.size,
            0
        );
        return new CleanableSummary({
            totalSize: totalSizeInBytes,
            totalItems: data.length,
        });
    } catch (e) {
        rethrowSimple(e);
    }
}

/**
 * Retrieves all deleted datasets of the current user that haven't been purged yet using pagination.
 * @param options Filtering options for pagination and sorting.
 * @returns Array of dataset objects with the fields defined in `datasetKeys` constant.
 */
export async function fetchDiscardedDatasets(options: PaginationOptions = {}): Promise<DiscardedDataset[]> {
    let params = "";
    if (options.sortBy) {
        const sortPostfix = options.sortDesc ? "-dsc" : "-asc";
        params += `order=${options.sortBy}${sortPostfix}&`;
    }
    if (options.limit) {
        params += `limit=${options.limit}&`;
    }
    if (options.offset) {
        params += `offset=${options.offset}&`;
    }
    const url = `${getAppRoot()}api/datasets?keys=${datasetKeys}&${discardedDatasetsQueryParams}&${params}`;
    try {
        const { data } = await axios.get(url);
        return data as DiscardedDataset[];
    } catch (e) {
        rethrowSimple(e);
    }
}

/**
 * Purges a collection of datasets.
 * @param datasetSourceIds Array of objects with datasets {id, src} to be purged.
 * @returns Result object with `success_count` and `errors`.
 */
export async function purgeDatasets(datasetSourceIds: DatasetSourceId[]): Promise<DeleteDatasetBatchResult> {
    const payload = {
        purge: true,
        datasets: datasetSourceIds,
    };
    const url = `${getAppRoot()}api/datasets`;
    try {
        const { data } = await axios.delete(url, { data: payload });
        return data;
    } catch (e) {
        rethrowSimple(e);
    }
}

/**
 * Purges a set of datasets instances (HDA, LDDA, ...) from disk and returns the total space freed in bytes
 * taking into account possible datasets that couldn't be deleted.
 * @param items Array of datasets to be removed from disk.
 *                         Each dataset must contain `id` and `size`.
 * @returns Information about the result of the cleanup operation.
 */
export async function cleanupDiscardedDatasets(items: CleanableItem[]): Promise<CleanupResult> {
    const resultResponse: CleanupResultResponse = { errors: [], totalFreeBytes: 0, totalItemCount: 0 };
    try {
        const datasetsTable = items.reduce(
            (acc: { [key: string]: CleanableItem }, item: CleanableItem) => ((acc[item.id] = item), acc),
            {}
        );

        const datasetSourceIds: DatasetSourceId[] = items.map((item: CleanableItem) => {
            const dataset = item as DiscardedDataset;
            return { id: dataset.id, src: dataset.hda_ldda };
        });

        const requestResult = await purgeDatasets(datasetSourceIds);

        resultResponse.totalItemCount = items.length;

        if (requestResult.errors) {
            resultResponse.errors = mapErrors(datasetsTable, requestResult.errors);

            const erroredIds = requestResult.errors?.reduce((acc: string[], error) => [...acc, error.dataset.id], []);

            resultResponse.totalFreeBytes = datasetSourceIds.reduce((partial_sum, item) => {
                if (erroredIds?.includes(item.id)) {
                    return partial_sum;
                } else {
                    return partial_sum + (datasetsTable[item.id]?.size ?? 0);
                }
            }, 0);
        }
    } catch (error) {
        resultResponse.errorMessage = error as string;
    }
    return new CleanupResult(resultResponse);
}

export async function fetchDiscardedHistoriesSummary(): Promise<CleanableSummary> {
    const summaryKeys = "size";
    const url = `${getAppRoot()}api/histories?keys=${summaryKeys}&${discardedHistoriesQueryParams}`;
    try {
        const { data } = await axios.get(url);
        const totalSizeInBytes = data.reduce(
            (partial_sum: number, item: DiscardedHistory) => partial_sum + item.size,
            0
        );
        return new CleanableSummary({
            totalSize: totalSizeInBytes,
            totalItems: data.length,
        });
    } catch (e) {
        rethrowSimple(e);
    }
}

export async function fetchDiscardedHistories(options: PaginationOptions = {}): Promise<DiscardedHistory[]> {
    let params = "";
    if (options.sortBy) {
        const sortPostfix = options.sortDesc ? "-dsc" : "-asc";
        params += `order=${options.sortBy}${sortPostfix}&`;
    }
    if (options.limit) {
        params += `limit=${options.limit}&`;
    }
    if (options.offset) {
        params += `offset=${options.offset}&`;
    }
    const url = `${getAppRoot()}api/histories?keys=${historyKeys}&${discardedHistoriesQueryParams}&${params}`;
    try {
        const { data } = await axios.get(url);
        return data as DiscardedHistory[];
    } catch (e) {
        rethrowSimple(e);
    }
}

async function purgeHistory(historyId: string) {
    const payload = {
        purge: true,
    };
    const url = `${getAppRoot()}api/histories/${historyId}`;
    try {
        const { data } = await axios.delete(url, { data: payload });
        return data;
    } catch (e) {
        rethrowSimple(e);
    }
}

export async function cleanupDiscardedHistories(histories: DiscardedHistory[]) {
    const resultResponse: CleanupResultResponse = { errors: [], totalFreeBytes: 0, totalItemCount: 0 };
    const historiesTable = histories.reduce(
        (acc: { [key: string]: DiscardedHistory }, item: DiscardedHistory) => ((acc[item.id] = item), acc),
        {}
    );
    // TODO: Promise.all() and do this in parallel?  Or add a bulk delete endpoint?
    try {
        for (const history of histories) {
            await purgeHistory(history.id);
            resultResponse.totalFreeBytes += historiesTable[history.id]?.size ?? 0;
            resultResponse.totalItemCount += 1;
        }
    } catch (error) {
        resultResponse.errorMessage = error as string;
    }

    return new CleanupResult(resultResponse);
}

/**
 * Maps the error messages with the dataset name for user display.
 * @param datasetsTable Datasets dictionary indexed by ID
 * @param errors List of errors associated with each dataset ID
 * @returns A list with the name of the dataset and the associated error message.
 */
function mapErrors(datasetsTable: { [key: string]: CleanableItem }, errors: DatasetErrorMessage[]): ItemError[] {
    return errors.map((error) => {
        const name = datasetsTable[error.dataset.id]?.name ?? "Unknown Dataset";
        return { name: name, reason: error.error_message };
    });
}
