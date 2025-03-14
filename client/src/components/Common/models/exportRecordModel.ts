import { formatDistanceToNow, parseISO } from "date-fns";

import {
    type ExportObjectRequestMetadata,
    type ExportObjectResultMetadata,
    type ModelStoreFormat,
    type ObjectExportTaskResponse,
    type StoreExportPayload,
} from "@/api";

export interface ExportParams {
    readonly modelStoreFormat: ModelStoreFormat;
    readonly includeFiles: boolean;
    readonly includeDeleted: boolean;
    readonly includeHidden: boolean;
}

export interface ExportRecord {
    readonly id: string;
    readonly isReady: boolean;
    readonly isPreparing: boolean;
    readonly isUpToDate: boolean;
    readonly hasFailed: boolean;
    readonly date: Date;
    readonly elapsedTime: string;
    readonly taskUUID: string;
    readonly importUri?: string;
    readonly canReimport: boolean;
    readonly stsDownloadId?: string;
    readonly isStsDownload: boolean;
    readonly canDownload: boolean;
    readonly modelStoreFormat: ModelStoreFormat;
    readonly exportParams?: ExportParams;
    readonly duration?: number | null;
    readonly canExpire: boolean;
    readonly isPermanent: boolean;
    readonly expirationDate?: Date;
    readonly expirationElapsedTime?: string;
    readonly hasExpired: boolean;
    readonly errorMessage?: string | null;
}

export class ExportParamsModel implements ExportParams {
    private _params: Partial<StoreExportPayload>;
    constructor(data: Partial<StoreExportPayload> = {}) {
        this._params = data;
    }

    get modelStoreFormat() {
        return this._params?.model_store_format ?? "tgz";
    }

    get includeFiles() {
        return Boolean(this._params?.include_files);
    }

    get includeDeleted() {
        return Boolean(this._params?.include_deleted);
    }

    get includeHidden() {
        return Boolean(this._params?.include_hidden);
    }

    public equals(otherExportParams?: ExportParams) {
        if (!otherExportParams) {
            return false;
        }
        return areEqual(this, otherExportParams);
    }
}

export function areEqual(params1?: ExportParams, params2?: ExportParams): boolean {
    if (!params1 || !params2) {
        return false;
    }
    return (
        params1.modelStoreFormat === params2.modelStoreFormat &&
        params1.includeFiles === params2.includeFiles &&
        params1.includeDeleted === params2.includeDeleted &&
        params1.includeHidden === params2.includeHidden
    );
}

export class ExportRecordModel implements ExportRecord {
    private _data: ObjectExportTaskResponse;
    private _expirationDate?: Date;
    private _requestMetadata?: ExportObjectRequestMetadata;
    private _resultMetadata?: ExportObjectResultMetadata | null;
    private _exportParameters?: ExportParamsModel;

    constructor(data: ObjectExportTaskResponse) {
        this._data = data;
        this._expirationDate = undefined;
        this._requestMetadata = data.export_metadata?.request_data;
        this._resultMetadata = data.export_metadata?.result_data;
        this._exportParameters = this._requestMetadata?.payload
            ? new ExportParamsModel(this._requestMetadata?.payload)
            : undefined;
    }

    get id() {
        return this._data.id;
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
        const requestUri = payload && "target_uri" in payload ? payload.target_uri : undefined;
        const resultUri = this._resultMetadata?.uri;
        return resultUri || requestUri;
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
        return this.exportParams?.modelStoreFormat ?? "tgz";
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

    get isPermanent() {
        return !this.canExpire;
    }

    get expirationDate() {
        if (this._expirationDate === undefined) {
            this._expirationDate = this.duration ? new Date(this.date.getTime() + this.duration * 1000) : undefined;
        }
        return this._expirationDate;
    }

    get expirationElapsedTime() {
        return this.canExpire && this.expirationDate
            ? formatDistanceToNow(this.expirationDate, { addSuffix: true })
            : undefined;
    }

    get hasExpired() {
        return Boolean(this.canExpire && this.expirationDate && Date.now() > this.expirationDate.getTime());
    }

    get errorMessage() {
        return this._data?.export_metadata?.result_data?.error;
    }
}
