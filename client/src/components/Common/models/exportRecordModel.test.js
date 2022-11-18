import { ExportRecordModel } from "./exportRecordModel";

const EXPORT_DATE = "2022-11-18T11:03:52.732355";
const STS_EXPORT_DURATION_IN_SECONDS = 86400;
const EXPECTED_EXPIRATION_DATE = () => {
    const expectedDate = new Date(EXPORT_DATE);
    expectedDate.setSeconds(expectedDate.getSeconds() + STS_EXPORT_DURATION_IN_SECONDS);
    return expectedDate;
};

const STS_DOWNLOAD_RECORD = {
    id: "03501d7626bd192f",
    ready: true,
    preparing: false,
    up_to_date: true,
    task_uuid: "35563335-e275-4520-80e8-885793279095",
    create_time: EXPORT_DATE,
    export_metadata: {
        request_data: {
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
        },
        result_data: {
            target_uri: null,
            short_term_storage_request_id: "08bf4cc3-758e-4a9d-9fe4-a89a0d0604c7",
        },
    },
};

describe("ExportRecordModel", () => {
    describe("STS Download Record", () => {
        const stsDownloadRecord = new ExportRecordModel(STS_DOWNLOAD_RECORD);
        it("should calculate the correct expiration date", () => {
            expect(stsDownloadRecord.canExpire).toBe(true);
            expect(stsDownloadRecord.expirationDate).toStrictEqual(EXPECTED_EXPIRATION_DATE());
        });
    });
});
