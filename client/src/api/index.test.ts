import { getFakeHistorySummary, getFakeHistorySummaryExtended, getFakeRegisteredUser } from "@tests/test-data";
import { describe, expect, it } from "vitest";

import { type AnonymousUser, type HistorySummaryExtended, isAnonymousUser, isRegisteredUser, userOwnsHistory } from ".";

const registeredUser = getFakeRegisteredUser({ id: "fake-user-id" });
const anonymousUser: AnonymousUser = {
    isAnonymous: true,
    total_disk_usage: 0,
    nice_total_disk_usage: "0.0 bytes",
};

const historySummary = getFakeHistorySummary({
    id: "1234",
    name: "test",
    update_time: "2021-09-01T00:00:00.000Z",
    url: "/history/1234",
});

function historyWithOwner(user_id: string | null, id = "1234"): HistorySummaryExtended {
    return getFakeHistorySummaryExtended({
        ...historySummary,
        id,
        url: `/history/${id}`,
        user_id,
    });
}

const registeredUsersHistory = historyWithOwner("fake-user-id");
const anotherUsersHistory = historyWithOwner("another-fake-user-id", "5678");
const anonymousUsersHistory = historyWithOwner(null);
const userCases = [
    { name: "registered user", user: registeredUser, registered: true, anonymous: false },
    { name: "anonymous user", user: anonymousUser, registered: false, anonymous: true },
    { name: "sessionless user", user: null, registered: false, anonymous: false },
];

describe("isRegisteredUser", () => {
    it.each(userCases)("returns $registered for a $name", ({ user, registered }) => {
        expect(isRegisteredUser(user)).toBe(registered);
    });
});

describe("isAnonymousUser", () => {
    it.each(userCases)("returns $anonymous for a $name", ({ user, anonymous }) => {
        expect(isAnonymousUser(user)).toBe(anonymous);
    });
});

describe("userOwnsHistory", () => {
    it.each([
        { name: "registered user's own history", user: registeredUser, history: registeredUsersHistory, owns: true },
        { name: "another user's history", user: registeredUser, history: anotherUsersHistory, owns: false },
        { name: "history without an owner ID", user: registeredUser, history: historySummary, owns: true },
        { name: "anonymous user's own history", user: anonymousUser, history: anonymousUsersHistory, owns: true },
        {
            name: "registered user's history for an anonymous user",
            user: anonymousUser,
            history: registeredUsersHistory,
            owns: false,
        },
        {
            name: "registered user's history for a sessionless user",
            user: null,
            history: registeredUsersHistory,
            owns: false,
        },
        {
            name: "history without an owner ID for a sessionless user",
            user: null,
            history: historySummary,
            owns: false,
        },
        {
            name: "anonymous user's history for a sessionless user",
            user: null,
            history: anonymousUsersHistory,
            owns: false,
        },
    ])("returns $owns for $name", ({ user, history, owns }) => {
        expect(userOwnsHistory(user, history)).toBe(owns);
    });
});
