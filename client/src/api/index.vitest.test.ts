import { getFakeRegisteredUser } from "@tests/test-data";

import {
    type AnonymousUser,
    type AnyHistory,
    type HistorySummary,
    type HistorySummaryExtended,
    isRegisteredUser,
    userOwnsHistory,
} from ".";

const REGISTERED_USER_ID = "fake-user-id";
const ANOTHER_USER_ID = "another-fake-user-id";
const ANONYMOUS_USER_ID = null;

const REGISTERED_USER = getFakeRegisteredUser({ id: REGISTERED_USER_ID });

const ANONYMOUS_USER: AnonymousUser = {
    isAnonymous: true,
    total_disk_usage: 0,
    nice_total_disk_usage: "0.0 bytes",
};

const SESSIONLESS_USER = null;

function createFakeHistory<T>(historyId: string = "fake-id", user_id?: string | null): T {
    const history: AnyHistory = {
        id: historyId,
        name: "test",
        model_class: "History",
        deleted: false,
        archived: false,
        purged: false,
        published: false,
        annotation: null,
        update_time: "2021-09-01T00:00:00.000Z",
        tags: [],
        url: `/history/${historyId}`,
        contents_active: { active: 0, deleted: 0, hidden: 0 },
        count: 0,
        size: 0,
    };
    if (user_id !== undefined) {
        (history as HistorySummaryExtended).user_id = user_id;
    }
    return history as T;
}

const HISTORY_OWNED_BY_REGISTERED_USER = createFakeHistory<HistorySummaryExtended>("1234", REGISTERED_USER_ID);
const HISTORY_OWNED_BY_ANOTHER_USER = createFakeHistory<HistorySummaryExtended>("5678", ANOTHER_USER_ID);
const HISTORY_OWNED_BY_ANONYMOUS_USER = createFakeHistory<HistorySummaryExtended>("1234", ANONYMOUS_USER_ID);
const HISTORY_SUMMARY_WITHOUT_USER_ID = createFakeHistory<HistorySummary>("1234");

describe("API Types Helpers", () => {
    describe("isRegisteredUser", () => {
        it("should return true for a registered user", () => {
            expect(isRegisteredUser(REGISTERED_USER)).toBe(true);
        });

        it("should return false for an anonymous user", () => {
            expect(isRegisteredUser(ANONYMOUS_USER)).toBe(false);
        });

        it("should return false for sessionless users", () => {
            expect(isRegisteredUser(SESSIONLESS_USER)).toBe(false);
        });
    });

    describe("isAnonymousUser", () => {
        it("should return true for an anonymous user", () => {
            expect(isRegisteredUser(ANONYMOUS_USER)).toBe(false);
        });

        it("should return false for a registered user", () => {
            expect(isRegisteredUser(REGISTERED_USER)).toBe(true);
        });

        it("should return false for sessionless users", () => {
            expect(isRegisteredUser(SESSIONLESS_USER)).toBe(false);
        });
    });

    describe("userOwnsHistory", () => {
        it("should return true for a registered user owning the history", () => {
            expect(userOwnsHistory(REGISTERED_USER, HISTORY_OWNED_BY_REGISTERED_USER)).toBe(true);
        });

        it("should return false for a registered user not owning the history", () => {
            expect(userOwnsHistory(REGISTERED_USER, HISTORY_OWNED_BY_ANOTHER_USER)).toBe(false);
        });

        it("should return true for a registered user owning a history without user_id", () => {
            expect(userOwnsHistory(REGISTERED_USER, HISTORY_SUMMARY_WITHOUT_USER_ID)).toBe(true);
        });

        it("should return true for an anonymous user owning a history with null user_id", () => {
            expect(userOwnsHistory(ANONYMOUS_USER, HISTORY_OWNED_BY_ANONYMOUS_USER)).toBe(true);
        });

        it("should return false for an anonymous user not owning a history", () => {
            expect(userOwnsHistory(ANONYMOUS_USER, HISTORY_OWNED_BY_REGISTERED_USER)).toBe(false);
        });

        it("should return false for sessionless users", () => {
            expect(userOwnsHistory(SESSIONLESS_USER, HISTORY_OWNED_BY_REGISTERED_USER)).toBe(false);
            expect(userOwnsHistory(SESSIONLESS_USER, HISTORY_SUMMARY_WITHOUT_USER_ID)).toBe(false);
            expect(userOwnsHistory(SESSIONLESS_USER, HISTORY_OWNED_BY_ANONYMOUS_USER)).toBe(false);
        });
    });
});
