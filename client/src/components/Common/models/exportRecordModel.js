export class ExportRecordModel {
    constructor(data) {
        this._data = data;
        this._expirationDate = undefined;
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

    get importUri() {
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

    get modelStoreFormat() {
        return this._data?.export_metadata?.request_data?.payload?.model_store_format;
    }

    get duration() {
        return this._data?.export_metadata?.request_data?.payload?.duration;
    }

    get canExpire() {
        return this.isStsDownload && !!this.duration;
    }

    get expirationDate() {
        if (this._expirationDate === undefined) {
            this._expirationDate = this.canExpire
                ? new Date(new Date(this.date).getTime() + this.duration * 1000)
                : null;
        }
        return this._expirationDate;
    }
}
