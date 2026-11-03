import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ExportRecordModel } from "./exportRecordModel";
import {
    EXPECTED_EXPIRATION_DATE,
    EXPIRED_STS_DOWNLOAD_RESPONSE,
    FAILED_DOWNLOAD_RESPONSE,
    FILE_SOURCE_STORE_RESPONSE,
    RECENT_STS_DOWNLOAD_RESPONSE,
} from "./testData/exportData";

describe("ExportRecordModel", () => {
    beforeEach(() => {
        vi.spyOn(Date, "now").mockReturnValue(new Date(RECENT_STS_DOWNLOAD_RESPONSE.create_time).getTime());
    });
    afterEach(() => {
        vi.restoreAllMocks();
    });
    describe("STS Download Record", () => {
        it("should be considered temporal (STS) when it has a short term storage ID defined", () => {
            const stsDownloadRecord = new ExportRecordModel(RECENT_STS_DOWNLOAD_RESPONSE);
            expect(stsDownloadRecord.isStsDownload).toBe(true);
            expect(stsDownloadRecord.stsDownloadId).toBeTruthy();
        });

        it("should allow download when ready and not yet expired", () => {
            const stsDownloadRecord = new ExportRecordModel(RECENT_STS_DOWNLOAD_RESPONSE);
            expect(stsDownloadRecord.isReady).toBe(true);
            expect(stsDownloadRecord.hasExpired).toBe(false);
            expect(stsDownloadRecord.canDownload).toBe(true);
        });
    });

    describe("Expired STS Download Record", () => {
        it("should calculate the correct expiration date", () => {
            const expiredDownloadRecord = new ExportRecordModel(EXPIRED_STS_DOWNLOAD_RESPONSE);
            expect(expiredDownloadRecord.canExpire).toBe(true);
            expect(expiredDownloadRecord.expirationDate).toStrictEqual(EXPECTED_EXPIRATION_DATE());
        });

        it("should not allow download when expired", () => {
            const expiredDownloadRecord = new ExportRecordModel(EXPIRED_STS_DOWNLOAD_RESPONSE);
            expect(expiredDownloadRecord.hasExpired).toBe(true);
            expect(expiredDownloadRecord.canDownload).toBe(false);
            expect(expiredDownloadRecord.isReady).toBe(false);
        });
    });

    it("expires only after the expiration instant", () => {
        const record = new ExportRecordModel(EXPIRED_STS_DOWNLOAD_RESPONSE);
        const expirationTime = EXPECTED_EXPIRATION_DATE().getTime();

        vi.mocked(Date.now).mockReturnValue(expirationTime);
        expect(record.hasExpired).toBe(false);
        expect(record.canDownload).toBe(true);

        vi.mocked(Date.now).mockReturnValue(expirationTime + 1);
        expect(record.hasExpired).toBe(true);
        expect(record.canDownload).toBe(false);
    });

    describe("Failed STS Download Record", () => {
        it("should not be downloadable", () => {
            const failedDownloadRecord = new ExportRecordModel(FAILED_DOWNLOAD_RESPONSE);
            expect(failedDownloadRecord.isReady).toBe(false);
            expect(failedDownloadRecord.isPreparing).toBe(false);
            expect(failedDownloadRecord.hasExpired).toBe(false);
            expect(failedDownloadRecord.canDownload).toBe(false);
        });
    });

    describe("File Source Storage Record", () => {
        it("should be importable", () => {
            const fileSourceRecord = new ExportRecordModel(FILE_SOURCE_STORE_RESPONSE);
            expect(fileSourceRecord.isReady).toBe(true);
            expect(fileSourceRecord.canReimport).toBe(true);
            expect(fileSourceRecord.importUri).toBeTruthy();
        });
    });
});
