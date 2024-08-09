import { GalaxyApi, type ModelStoreFormat, type ObjectExportTaskResponse } from "@/api";
import { type ExportRecord, ExportRecordModel } from "@/components/Common/models/exportRecordModel";
import { DEFAULT_EXPORT_PARAMS } from "@/composables/shortTermStorage";
import { rethrowSimple } from "@/utils/simple-error";

/**
 * A list of objects with the available export formats IDs and display names.
 */
export const AVAILABLE_EXPORT_FORMATS: { id: ModelStoreFormat; name: string }[] = [
    { id: "rocrate.zip", name: "RO-Crate" },
    { id: "tar.gz", name: "Compressed TGZ" },
];

/**
 * Gets a list of export records for the given history.
 * @param historyId the encoded ID of the history
 * @param params query and pagination params
 * @returns a promise with a list of export records associated with the given history.
 */
export async function fetchHistoryExportRecords(historyId: string) {
    const { data, error } = await GalaxyApi().GET("/api/histories/{history_id}/exports", {
        params: {
            path: { history_id: historyId },
            header: {
                accept: "application/vnd.galaxy.task.export+json",
            },
        },
    });

    if (error) {
        rethrowSimple(error);
    }

    return data.map((item) => new ExportRecordModel(item as ObjectExportTaskResponse));
}

/**
 *
 * @param historyId the encoded ID of the history
 * @param exportDirectory the output directory in the file source
 * @param fileName the name of the output archive
 * @param exportParams additional parameters to configure the export
 * @returns A promise with the async task response that can be used to track the export progress.
 */
export async function exportHistoryToFileSource(
    historyId: string,
    exportDirectory: string,
    fileName: string,
    exportParams = DEFAULT_EXPORT_PARAMS
) {
    const exportDirectoryUri = `${exportDirectory}/${fileName}.${exportParams.modelStoreFormat}`;

    const { data, error } = await GalaxyApi().POST("/api/histories/{history_id}/write_store", {
        params: {
            path: { history_id: historyId },
        },
        body: {
            target_uri: exportDirectoryUri,
            model_store_format: exportParams.modelStoreFormat,
            include_files: exportParams.includeFiles,
            include_deleted: exportParams.includeDeleted,
            include_hidden: exportParams.includeHidden,
        },
    });

    if (error) {
        rethrowSimple(error);
    }

    return data;
}

/**
 * Imports a new history using the information stored in the given export record.
 * @param record The export record to be imported
 * @returns A promise with the async task response that can be used to track the import progress.
 */
export async function reimportHistoryFromRecord(record: ExportRecord) {
    const { data, error } = await GalaxyApi().POST("/api/histories/from_store_async", {
        body: {
            store_content_uri: record.importUri,
            model_store_format: record.modelStoreFormat,
        },
    });

    if (error) {
        rethrowSimple(error);
    }

    return data;
}
