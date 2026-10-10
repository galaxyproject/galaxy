import { describe, expect, it } from "vitest";

import {
    getHistoryUploadActionErrorMessage,
    getHistoryUploadBlockReason,
    getHistoryUploadWarningMessage,
} from "./historyUpload";

describe("historyUpload", () => {
    it.each([
        { reason: "archived", history: { archived: true, deleted: false } },
        { reason: "deleted", history: { archived: false, deleted: true } },
    ])("blocks uploads and explains why the history is $reason", ({ reason, history }) => {
        const blockReason = getHistoryUploadBlockReason(history);

        expect(blockReason).toBe(reason);
        expect(getHistoryUploadWarningMessage(blockReason)).toContain(reason);
        expect(getHistoryUploadActionErrorMessage(blockReason)).toContain(reason);
    });

    it("returns null for active histories", () => {
        const reason = getHistoryUploadBlockReason({ archived: false, deleted: false });
        expect(reason).toBeNull();
        expect(getHistoryUploadWarningMessage(reason)).toBe("");
        expect(getHistoryUploadActionErrorMessage(reason)).toBe("");
    });
});
