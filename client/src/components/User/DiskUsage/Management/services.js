import axios from "axios";
import { getAppRoot } from "onload/loadConfig";
import { rethrowSimple } from "utils/simple-error";

const datasetKeys = "id,name,size,update_time";

/**
 * Retrieves all deleted datasets of the current user
 * that haven't been purged yet.
 * @returns {Array} Array of dataset objects with the fields defined in `datasetKeys` constant.
 */
export async function fetchDiscardedDatasets() {
    const isDataset = "q=history_content_type-eq&qv=dataset";
    const isDeleted = "q=deleted-eq&qv=True";
    const isNotPurged = "q=purged-eq&qv=False";
    const url = `${getAppRoot()}api/datasets?keys=${datasetKeys}&${isDataset}&${isDeleted}&${isNotPurged}`;
    try {
        const { data } = await axios.get(url);
        return data;
    } catch (e) {
        rethrowSimple(e);
    }
}

/**
 * Purges a collection of datasets.
 * @param {Array} datasetIds Array of dataset IDs to be purged.
 * @returns {Object} Result object with `success_count` and `errors`.
 */
export async function purgeDatasets(datasetIds) {
    const payload = {
        purge: true,
        ids: datasetIds,
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
 * Purges a set of datasets from disk and returns the total space freed in bytes
 * taking into account possible datasets that couldn't be deleted.
 * @param {Array} datasets Array of datasets to be removed from disk.
 *                         Each dataset must contain `id` and `size`.
 * @returns {Object} Contains the total bytes cleaned up and the list of errors if any.
 */
export async function cleanupDatasets(datasets) {
    const datasetsTable = datasets.reduce((acc, item) => ((acc[item.id] = item), acc), {});
    const datasetIds = Object.keys(datasetsTable);
    const requestResult = await purgeDatasets(datasetIds);
    const erroredIds = requestResult.errors.reduce((acc, item) => [...acc, item["id"]], []);
    const totalFreeBytes = datasetIds.reduce(
        (partial_sum, id) => partial_sum + (erroredIds.includes(id) ? 0 : datasetsTable[id]["size"]),
        0
    );
    return {
        totalFreeBytes: totalFreeBytes,
        errors: requestResult.errors,
        success: totalFreeBytes > 0,
    };
}
