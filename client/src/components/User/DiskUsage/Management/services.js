import axios from "axios";
import { getAppRoot } from "onload/loadConfig";
import { rethrowSimple } from "utils/simple-error";
import { CleanableSummary, CleanupResult } from "./Cleanup/model";

const datasetKeys = "id,name,size,update_time,hda_ldda";
const isDataset = "q=history_content_type-eq&qv=dataset";
const isDeleted = "q=deleted-eq&qv=True";
const isNotPurged = "q=purged-eq&qv=False";
const maxItemsToFetch = 500;
const discardedDatasetsQueryParams = `${isDataset}&${isDeleted}&${isNotPurged}&limit=${maxItemsToFetch}`;

const historyKeys = "id,name,size,update_time";
const discardedHistoriesQueryParams = `&${isDeleted}&${isNotPurged}&limit=${maxItemsToFetch}`;

/**
 * Calculates the total amount of bytes that can be cleaned by permanently removing
 * deleted datasets.
 * @returns {CleanableSummary} Object containing information about how much can be cleaned.
 */
export async function fetchDiscardedDatasetsSummary() {
    //TODO: possible optimization -> moving this to specific API endpoint so we don't have to parse
    //      potentially a huge number of items
    const summaryKeys = "size";
    const url = `${getAppRoot()}api/datasets?keys=${summaryKeys}&${discardedDatasetsQueryParams}`;
    try {
        const { data } = await axios.get(url);
        const totalSizeInBytes = data.reduce((partial_sum, item) => partial_sum + item.size, 0);
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
 * @param {Object} options Filtering options for pagination and sorting.
 * @returns {Array} Array of dataset objects with the fields defined in `datasetKeys` constant.
 */
export async function fetchDiscardedDatasets(options = {}) {
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
        return data;
    } catch (e) {
        rethrowSimple(e);
    }
}

/**
 * Purges a collection of datasets.
 * @param {Array} datasetSourceIds Array of objects with datasets {id, src} to be purged.
 * @returns {Object} Result object with `success_count` and `errors`.
 */
export async function purgeDatasets(datasetSourceIds) {
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
 * @param {Array} datasets Array of datasets to be removed from disk.
 *                         Each dataset must contain `id` and `size`.
 * @returns {CleanupResult}
 */
export async function cleanupDatasets(datasets) {
    const result = new CleanupResult();
    try {
        const datasetsTable = datasets.reduce((acc, item) => ((acc[item.id] = item), acc), {});
        const datasetSourceIds = datasets.map((dataset) => {
            return { id: dataset.id, src: dataset.hda_ldda };
        });
        const requestResult = await purgeDatasets(datasetSourceIds);
        result.totalItemCount = datasets.length;
        result.errors = mapErrors(datasetsTable, requestResult.errors);
        const erroredIds = requestResult.errors.reduce((acc, error) => [...acc, error.dataset.id], []);
        result.totalFreeBytes = datasetSourceIds.reduce(
            (partial_sum, item) => partial_sum + (erroredIds.includes(item.id) ? 0 : datasetsTable[item.id].size),
            0
        );
    } catch (error) {
        result.errorMessage = error;
    }
    return result;
}

export async function fetchDiscardedHistoriesSummary() {
    const summaryKeys = "size";
    const url = `${getAppRoot()}api/histories?keys=${summaryKeys}&${discardedHistoriesQueryParams}`;
    try {
        const { data } = await axios.get(url);
        const totalSizeInBytes = data.reduce((partial_sum, item) => partial_sum + item.size, 0);
        return new CleanableSummary({
            totalSize: totalSizeInBytes,
            totalItems: data.length,
        });
    } catch (e) {
        rethrowSimple(e);
    }
}

export async function fetchDiscardedHistories(options = {}) {
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
        return data;
    } catch (e) {
        rethrowSimple(e);
    }
}

async function purgeHistory(historyId) {
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

export async function cleanupHistories(histories) {
    const result = new CleanupResult();
    const historiesTable = histories.reduce((acc, item) => ((acc[item.id] = item), acc), {});
    // TODO: Promise.all() and do this in parallel?  Or add a bulk delete endpoint?
    try {
        for (const history of histories) {
            const requestResult = await purgeHistory(history.id);
            console.debug(requestResult);
            result.totalFreeBytes += historiesTable[history.id].size;
            result.totalItemCount += 1;
        }
    } catch (error) {
        result.errorMessage = error;
    }
    return result;
}

/**
 * Maps the error messages with the dataset name for user display.
 * @param datasetsTable Datasets dictionary indexed by ID
 * @param errors List of errors associated with each dataset ID
 * @returns A list with the name of the dataset and the associated error message.
 */
function mapErrors(datasetsTable, errors) {
    return errors.map((error) => {
        const name = datasetsTable[error.dataset.id].name;
        return { name: name, reason: error.error_message };
    });
}
