import axios from "axios";
import { rethrowSimple } from "utils/simple-error";
import { safePath } from "utils/redirect";
import { ExportRecordModel } from "components/Common/models/exportRecordModel";

const DEFAULT_EXPORT_PARAMS = {
    modelStoreFormat: "rocrate.zip",
    includeFiles: true,
    includeDeleted: false,
    includeHidden: false,
};

export const AVAILABLE_EXPORT_FORMATS = [
    { id: "rocrate.zip", name: "RO-Crate" },
    { id: "tar.gz", name: "Compressed TGZ" },
];

export class ExportParamsModel {
    constructor(params = DEFAULT_EXPORT_PARAMS) {
        this._params = params;
    }

    get modelStoreFormat() {
        return this._params.modelStoreFormat;
    }

    get includeFiles() {
        return this._params.includeFiles;
    }

    get includeDeleted() {
        return this._params.includeDeleted;
    }

    get includeHidden() {
        return this._params.includeHidden;
    }
}

export class HistoryExportService {
    /**
     * Gets the default options to export a history.
     */
    get defaultExportParams() {
        return DEFAULT_EXPORT_PARAMS;
    }

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

    async exportToFileSource(historyId, exportDirectory, fileName, exportParams = DEFAULT_EXPORT_PARAMS) {
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

    async reimportHistoryFromRecord(record) {
        const writeStorePayload = {
            store_content_uri: record.importUri,
            model_store_format: record.modelStoreFormat,
        };
        return axios.post(`/api/histories/from_store_async`, writeStorePayload);
    }
}
