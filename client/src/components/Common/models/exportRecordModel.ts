import { formatDistanceToNow, parseISO } from "date-fns";
import type { components } from "schema";

type StoreExportPayload = components["schemas"]["StoreExportPayload"];
type ExportObjectRequestMetadata = components["schemas"]["ExportObjectRequestMetadata"];
export type ObjectExportTaskResponse = components["schemas"]["ObjectExportTaskResponse"];

export class ExportRecordModel {
    private _data: ObjectExportTaskResponse;
    private _expirationDate?: Date | null;
    private _requestMetadata?: ExportObjectRequestMetadata;

    constructor(data: ObjectExportTaskResponse) {
        this._data = data;
        this._expirationDate = undefined;
        this._requestMetadata = data.export_metadata?.request_data;
    }

    get isReady() {
        return (this._data.ready && !this.hasExpired) ?? false;
    }

    get isPreparing() {
        return this._data.preparing ?? false;
    }

    get isUpToDate() {
        return this._data.up_to_date ?? false;
    }

    get hasFailed() {
        return !this.isReady && !this.isPreparing && !this.hasExpired;
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
        const payload = this._requestMetadata?.payload;
        return payload && "target_uri" in payload ? payload.target_uri : undefined;
    }

    get canReimport() {
        return this.isReady && Boolean(this.importUri);
    }

    get stsDownloadId() {
        const payload = this._requestMetadata?.payload;
        return payload && "short_term_storage_request_id" in payload
            ? payload.short_term_storage_request_id
            : undefined;
    }

    get isStsDownload() {
        return Boolean(this.stsDownloadId);
    }

    get canDownload() {
        return this.isReady && this.isStsDownload && !this.hasExpired;
    }

    get modelStoreFormat() {
        return this.exportParams?.model_store_format;
    }

    get exportParams(): StoreExportPayload | undefined {
        return this._requestMetadata?.payload;
    }

    get duration() {
        const payload = this._requestMetadata?.payload;
        return payload && "duration" in payload ? payload.duration : undefined;
    }

    get canExpire() {
        return this.isStsDownload && Boolean(this.duration);
    }

    get expirationDate() {
        if (this._expirationDate === undefined) {
            this._expirationDate = this.duration ? new Date(this.date.getTime() + this.duration * 1000) : null;
        }
        return this._expirationDate;
    }

    get expirationElapsedTime() {
        return this.canExpire && this.expirationDate
            ? formatDistanceToNow(this.expirationDate, { addSuffix: true })
            : null;
    }

    get hasExpired() {
        return this.canExpire && this.expirationDate && Date.now() > this.expirationDate.getTime();
    }

    get errorMessage() {
        return this._data?.export_metadata?.result_data?.error;
    }
}
