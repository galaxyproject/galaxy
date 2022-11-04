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

    // import_uri doesn't work for downloads
    get canReimport() {
        return this._data?.export_metadata?.result_data?.import_uri !== undefined;
    }

    get importLink() {
        return this._data?.export_metadata?.result_data?.import_uri;
    }
}
