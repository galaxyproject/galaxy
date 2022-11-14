export class ExportRecordModel {
    constructor(data) {
        this._data = data;
    }

    get isReady() {
        return this._data.ready || false;
    }

    get isPreparing() {
        return this._data.preparing || false;
    }

    get isUpToDate() {
        return this._data.up_to_date || false;
    }

    get hasFailed() {
        return !this.isReady && !this.isPreparing;
    }

    get date() {
        return this._data.create_time;
    }

    get taskUUID() {
        return this._data.task_uuid;
    }

    get canReimport() {
        return this.isReady && !!this._data?.export_metadata?.result_data?.target_uri;
    }

    get importLink() {
        return this._data?.export_metadata?.result_data?.target_uri;
    }

    get isStsDownload() {
        return !!this._data?.export_metadata?.result_data?.short_term_storage_request_id;
    }

    get stsDownloadId() {
        return this._data?.export_metadata?.result_data?.short_term_storage_request_id;
    }

    get canDownload() {
        return this.isReady && this.isStsDownload;
    }
}
