import { ExportRecordModel } from "@/components/Common/models/exportRecordModel";
import type { ObjectExportTaskResponse } from "@/components/Common/models/exportRecordModel";
import { DEFAULT_EXPORT_PARAMS } from "@/composables/shortTermStorage";
import type { components } from "@/schema";
import { fetcher } from "@/schema";

type ModelStoreFormat = components["schemas"]["ModelStoreFormat"];

const _getExportRecords = fetcher.path("/api/histories/{history_id}/exports").method("get").create();
const _exportToFileSource = fetcher.path("/api/histories/{history_id}/write_store").method("post").create();
const _importFromStoreAsync = fetcher.path("/api/histories/from_store_async").method("post").create();

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
export async function getExportRecords(historyId: string) {
    const response = await _getExportRecords(
        {
            history_id: historyId,
        },
        {
            headers: {
                Accept: "application/vnd.galaxy.task.export+json",
            },
        }
    );
    return response.data.map((item: unknown) => new ExportRecordModel(item as ObjectExportTaskResponse));
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

    return _exportToFileSource({
        history_id: historyId,
        target_uri: exportDirectoryUri,
        model_store_format: exportParams.modelStoreFormat as ModelStoreFormat,
        include_files: exportParams.includeFiles,
        include_deleted: exportParams.includeDeleted,
        include_hidden: exportParams.includeHidden,
    });
}

/**
 * Imports a new history using the information stored in the given export record.
 * @param record The export record to be imported
 * @returns A promise with the request response
 */
export async function reimportHistoryFromRecord(record: ExportRecordModel) {
    return _importFromStoreAsync({
        store_content_uri: record.importUri,
        model_store_format: record.modelStoreFormat,
    });
}
