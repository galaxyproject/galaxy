import axios from "axios";
import { rethrowSimple } from "utils/simple-error";
import { safePath } from "utils/redirect";
import { ExportRecordModel } from "components/Common/models/exportRecordModel";
import { DEFAULT_EXPORT_PARAMS } from "composables/shortTermStorage";

/**
 * A list of objects with the available export formats IDs and display names.
 */
export const AVAILABLE_EXPORT_FORMATS: Array<{ id: string; name: string }> = [
    { id: "rocrate.zip", name: "RO-Crate" },
    { id: "tar.gz", name: "Compressed TGZ" },
];

/**
 * Gets a list of export records for the given history.
 * @param historyId the encoded ID of the history
 * @param params query and pagination params
 * @returns a promise with a list of export records associated with the given history.
 */
export async function getExportRecords(
    historyId: string,
    params: { offset?: number; limit?: number } = { offset: undefined, limit: undefined }
): Promise<ExportRecordModel[]> {
    const url = safePath(`/api/histories/${historyId}/exports`);
    try {
        const response = await axios.get(url, {
            headers: { Accept: "application/vnd.galaxy.task.export+json" },
            params: params,
        });
        return response.data.map((item) => new ExportRecordModel(item));
    } catch (e) {
        rethrowSimple(e);
    }
}

/**
 *
 * @param historyId the encoded ID of the history
 * @param exportDirectory the output directory in the file source
 * @param fileName the name of the output archive
 * @param exportParams additional parameters to configure the export
 * @returns A promise with the request response
 */
export async function exportToFileSource(
    historyId: string,
    exportDirectory: string,
    fileName: string,
    exportParams = DEFAULT_EXPORT_PARAMS
) {
    const exportDirectoryUri = `${exportDirectory}/${fileName}.${exportParams.modelStoreFormat}`;
    const writeStorePayload = {
        target_uri: exportDirectoryUri,
        model_store_format: exportParams.modelStoreFormat,
        include_files: exportParams.includeFiles,
        include_deleted: exportParams.includeDeleted,
        include_hidden: exportParams.includeHidden,
    };
    return axios.post(`/api/histories/${historyId}/write_store`, writeStorePayload);
}

/**
 * Imports a new history using the information stored in the given export record.
 * @param record The export record to be imported
 * @returns A promise with the request response
 */
export async function reimportHistoryFromRecord(record: ExportRecordModel) {
    const writeStorePayload = {
        store_content_uri: record.importUri,
        model_store_format: record.modelStoreFormat,
    };
    return axios.post(`/api/histories/from_store_async`, writeStorePayload);
}
