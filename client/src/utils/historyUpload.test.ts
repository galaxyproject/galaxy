import { describe, expect, it } from "vitest";

import {
    getHistoryUploadActionErrorMessage,
    getHistoryUploadBlockReason,
    getHistoryUploadWarningMessage,
} from "./historyUpload";

describe("historyUpload", () => {
    it("returns archived when history is archived", () => {
        const reason = getHistoryUploadBlockReason({ archived: true, deleted: false });
        expect(reason).toBe("archived");
        expect(getHistoryUploadWarningMessage(reason)).toContain("archived");
        expect(getHistoryUploadActionErrorMessage(reason)).toContain("archived");
    });

    it("returns deleted when history is deleted", () => {
        const reason = getHistoryUploadBlockReason({ archived: false, deleted: true });
        expect(reason).toBe("deleted");
        expect(getHistoryUploadWarningMessage(reason)).toContain("deleted");
        expect(getHistoryUploadActionErrorMessage(reason)).toContain("deleted");
    });

    it("returns null for active histories", () => {
        const reason = getHistoryUploadBlockReason({ archived: false, deleted: false });
        expect(reason).toBeNull();
        expect(getHistoryUploadWarningMessage(reason)).toBe("");
        expect(getHistoryUploadActionErrorMessage(reason)).toBe("");
    });
});
