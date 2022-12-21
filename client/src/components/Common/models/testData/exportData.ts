import { ExportRecordModel } from "@/components/Common/models/exportRecordModel";
import type { components } from "@/schema";

type ObjectExportTaskResponse = components["schemas"]["ObjectExportTaskResponse"];
type ExportObjectRequestMetadata = components["schemas"]["ExportObjectRequestMetadata"];
type ExportObjectResultMetadata = components["schemas"]["ExportObjectResultMetadata"];

const PAST_EXPORT_DATE = new Date("11 November 2022 14:48 UTC").toISOString();
const RECENT_EXPORT_DATE = new Date().toISOString();
const STS_EXPORT_DURATION_IN_SECONDS = 86400;
export const EXPECTED_EXPIRATION_DATE = () => {
    const expectedDate = new Date(PAST_EXPORT_DATE);
    expectedDate.setSeconds(expectedDate.getSeconds() + STS_EXPORT_DURATION_IN_SECONDS);
    return expectedDate;
};

const FAKE_STS_DOWNLOAD_REQUEST_DATA: ExportObjectRequestMetadata = {
    object_id: "3cc0effd29705aa3",
    object_type: "history",
    user_id: "f597429621d6eb2b",
    payload: {
        model_store_format: "rocrate.zip",
        include_files: true,
        include_deleted: false,
        include_hidden: false,
        short_term_storage_request_id: "08bf4cc3-758e-4a9d-9fe4-a89a0d0604c7",
        duration: STS_EXPORT_DURATION_IN_SECONDS,
    },
};

const FAKE_FILE_SOURCE_REQUEST_DATA: ExportObjectRequestMetadata = {
    object_id: "3cc0effd29705aa3",
    object_type: "history",
    user_id: "f597429621d6eb2b",
    payload: {
        model_store_format: "tar.gz",
        include_files: true,
        include_deleted: false,
        include_hidden: false,
        target_uri: "gxfiles://fake-target-uri/test.tar.gz",
    },
};

const SUCCESS_EXPORT_RESULT_DATA: ExportObjectResultMetadata = {
    success: true,
    error: undefined,
};

const FAILED_EXPORT_RESULT_DATA: ExportObjectResultMetadata = {
    success: false,
    error: "Fake Error Message",
};

export const RECENT_STS_DOWNLOAD_RESPONSE: ObjectExportTaskResponse = {
    id: "FAKE_RECENT_DOWNLOAD_ID",
    ready: true,
    preparing: false,
    up_to_date: true,
    task_uuid: "35563335-e275-4520-80e8-885793279095",
    create_time: RECENT_EXPORT_DATE,
    export_metadata: {
        request_data: FAKE_STS_DOWNLOAD_REQUEST_DATA,
        result_data: SUCCESS_EXPORT_RESULT_DATA,
    },
};

export const EXPIRED_STS_DOWNLOAD_RESPONSE: ObjectExportTaskResponse = {
    id: "FAKE_EXPIRED_DOWNLOAD_ID",
    ready: true,
    preparing: false,
    up_to_date: true,
    task_uuid: "35563335-e275-4520-80e8-885793279095",
    create_time: PAST_EXPORT_DATE,
    export_metadata: {
        request_data: FAKE_STS_DOWNLOAD_REQUEST_DATA,
        result_data: SUCCESS_EXPORT_RESULT_DATA,
    },
};

export const FAILED_DOWNLOAD_RESPONSE: ObjectExportTaskResponse = {
    id: "FAKE_FAILED_DOWNLOAD_ID",
    ready: false,
    preparing: false,
    up_to_date: true,
    task_uuid: "35563335-e275-4520-80e8-885793279095",
    create_time: RECENT_EXPORT_DATE,
    export_metadata: {
        request_data: FAKE_STS_DOWNLOAD_REQUEST_DATA,
        result_data: FAILED_EXPORT_RESULT_DATA,
    },
};

export const FILE_SOURCE_STORE_RESPONSE: ObjectExportTaskResponse = {
    id: "FAKE_RECENT_DOWNLOAD_ID",
    ready: true,
    preparing: false,
    up_to_date: true,
    task_uuid: "35563335-e275-4520-80e8-885793279095",
    create_time: RECENT_EXPORT_DATE,
    export_metadata: {
        request_data: FAKE_FILE_SOURCE_REQUEST_DATA,
        result_data: SUCCESS_EXPORT_RESULT_DATA,
    },
};

export const EXPIRED_STS_DOWNLOAD_RECORD = new ExportRecordModel(EXPIRED_STS_DOWNLOAD_RESPONSE);
export const FILE_SOURCE_STORE_RECORD = new ExportRecordModel(FILE_SOURCE_STORE_RESPONSE);
export const RECENT_STS_DOWNLOAD_RECORD = new ExportRecordModel(RECENT_STS_DOWNLOAD_RESPONSE);
