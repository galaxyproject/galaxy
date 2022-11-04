import axios from "axios";
import { rethrowSimple } from "utils/simple-error";
import { safePath } from "utils/redirect";
import { ExportRecordModel } from "components/Common/models/exportRecordModel";

export class HistoryExportServices {
    /**
     * Gets a list of export records for the given history.
     * @param {String} historyId
     * @returns {Promise<ExportRecordModel[]>}
     */
    async getExportRecords(historyId, params = { offset: undefined, limit: undefined }) {
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
     * Gets the latest export record for the given history.
     * @param {String} historyId
     * @returns {Promise<ExportRecordModel|null>}
     */
    async getLatestExportRecord(historyId) {
        try {
            const records = await this.getExportRecords(historyId, { limit: 1 });
            return records.length ? records.at(0) : null;
        } catch (e) {
            rethrowSimple(e);
        }
    }

    async exportToFileSource(
        historyId,
        exportDirectory,
        fileName,
        options = { exportFormat: "rocrate.zip", include_files: true, include_deleted: false, include_hidden: false }
    ) {
        const exportDirectoryUri = `${exportDirectory}/${fileName}.${options.exportFormat}`;
        const writeStoreParams = {
            target_uri: exportDirectoryUri,
            model_store_format: options.exportFormat,
            include_files: options.include_files,
            include_deleted: options.include_deleted,
            include_hidden: options.include_hidden,
        };
        return axios.post(`/api/histories/${historyId}/write_store`, writeStoreParams);
    }

    async reimportHistoryFromRecord(record) {
        console.debug("TODO: Reimport from", record.importLink);
    }
}
