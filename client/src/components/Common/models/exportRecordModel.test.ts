import { ExportRecordModel } from "./exportRecordModel";
import {
    EXPECTED_EXPIRATION_DATE,
    EXPIRED_STS_DOWNLOAD_RESPONSE,
    FAILED_DOWNLOAD_RESPONSE,
    FILE_SOURCE_STORE_RESPONSE,
    RECENT_STS_DOWNLOAD_RESPONSE,
} from "./testData/exportData";

describe("ExportRecordModel", () => {
    describe("STS Download Record", () => {
        const stsDownloadRecord = new ExportRecordModel(RECENT_STS_DOWNLOAD_RESPONSE);

        it("should be considered temporal (STS) when it has a short term storage ID defined", () => {
            expect(stsDownloadRecord.isStsDownload).toBe(true);
            expect(stsDownloadRecord.stsDownloadId).toBeTruthy();
        });

        it("should allow download when ready and not yet expired", () => {
            expect(stsDownloadRecord.isReady).toBe(true);
            expect(stsDownloadRecord.hasExpired).toBe(false);
            expect(stsDownloadRecord.canDownload).toBe(true);
        });
    });

    describe("Expired STS Download Record", () => {
        const expiredDownloadRecord = new ExportRecordModel(EXPIRED_STS_DOWNLOAD_RESPONSE);

        it("should calculate the correct expiration date", () => {
            expect(expiredDownloadRecord.canExpire).toBe(true);
            expect(expiredDownloadRecord.expirationDate).toStrictEqual(EXPECTED_EXPIRATION_DATE());
        });

        it("should not allow download when expired", () => {
            expect(expiredDownloadRecord.hasExpired).toBe(true);
            expect(expiredDownloadRecord.canDownload).toBe(false);
            expect(expiredDownloadRecord.isReady).toBe(false);
        });
    });

    describe("Failed STS Download Record", () => {
        const failedDownloadRecord = new ExportRecordModel(FAILED_DOWNLOAD_RESPONSE);

        it("should not be downloadable", () => {
            expect(failedDownloadRecord.isReady).toBe(false);
            expect(failedDownloadRecord.isPreparing).toBe(false);
            expect(failedDownloadRecord.hasExpired).toBe(false);
            expect(failedDownloadRecord.canDownload).toBe(false);
        });
    });

    describe("File Source Storage Record", () => {
        const failedDownloadRecord = new ExportRecordModel(FILE_SOURCE_STORE_RESPONSE);

        it("should be importable", () => {
            expect(failedDownloadRecord.isReady).toBe(true);
            expect(failedDownloadRecord.canReimport).toBe(true);
            expect(failedDownloadRecord.importUri).toBeTruthy();
        });
    });
});
