import { formatDistanceToNow, parseISO } from "date-fns";
import type { components } from "@/schema";

type ExportObjectRequestMetadata = components["schemas"]["ExportObjectRequestMetadata"];

export type StoreExportPayload = components["schemas"]["StoreExportPayload"];
export type ObjectExportTaskResponse = components["schemas"]["ObjectExportTaskResponse"];

export class ExportParamsModel {
    private _params: StoreExportPayload;
    constructor(data: StoreExportPayload = {}) {
        this._params = data;
    }

    get modelStoreFormat() {
        return this._params?.model_store_format;
    }

    get includeFiles() {
        return this._params?.include_files;
    }

    get includeDeleted() {
        return this._params?.include_deleted;
    }

    get includeHidden() {
        return this._params?.include_hidden;
    }

    public equals(otherExportParams?: ExportParamsModel) {
        if (!otherExportParams) {
            return false;
        }
        return (
            this.modelStoreFormat === otherExportParams.modelStoreFormat &&
            this.includeFiles === otherExportParams.includeFiles &&
            this.includeDeleted === otherExportParams.includeDeleted &&
            this.includeHidden === otherExportParams.includeHidden
        );
    }
}

export class ExportRecordModel {
    private _data: ObjectExportTaskResponse;
    private _expirationDate?: Date | null;
    private _requestMetadata?: ExportObjectRequestMetadata;
    private _exportParameters?: ExportParamsModel;

    constructor(data: ObjectExportTaskResponse) {
        this._data = data;
        this._expirationDate = undefined;
        this._requestMetadata = data.export_metadata?.request_data;
        this._exportParameters = this._requestMetadata?.payload
            ? new ExportParamsModel(this._requestMetadata?.payload)
            : undefined;
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
        return this.exportParams?.modelStoreFormat;
    }

    get exportParams() {
        return this._exportParameters;
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
