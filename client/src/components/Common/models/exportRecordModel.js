import { formatDistanceToNow, parseISO } from "date-fns";

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
        return parseISO(`${this._data.create_time}Z`);
    }

    get elapsedTime() {
        return formatDistanceToNow(this.date, { addSuffix: true });
    }

    get taskUUID() {
        return this._data.task_uuid;
    }

    get importUri() {
        return this._data?.export_metadata?.request_data?.payload?.target_uri;
    }

    get canReimport() {
        return this.isReady && !!this.importUri;
    }

    get stsDownloadId() {
        return this._data?.export_metadata?.request_data?.payload?.short_term_storage_request_id;
    }

    get isStsDownload() {
        return !!this.stsDownloadId;
    }

    get canDownload() {
        return this.isReady && this.isStsDownload && !this.hasExpired;
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
            this._expirationDate = this.canExpire ? new Date(this.date.getTime() + this.duration * 1000) : null;
        }
        return this._expirationDate;
    }

    get expirationElapsedTime() {
        return this.canExpire ? formatDistanceToNow(this.expirationDate, { addSuffix: true }) : null;
    }

    get hasExpired() {
        return this.canExpire && Date.now() > this.expirationDate;
    }
}
