import { getFakeHistorySummary, getFakeRegisteredUser } from "@tests/test-data";
import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import type { AnonymousUser, AnyUser, HistorySummary } from "@/api";

import HistoryMessages from "./HistoryMessages.vue";

const localVue = getLocalVue();

const MESSAGES = "[data-description='history messages']";
const OVER_QUOTA_MESSAGE = "[data-description='over quota message']";

const CURRENT_USER = getFakeRegisteredUser({ id: "current_user_id" });

function mountHistoryMessages(currentUser: AnyUser, history: HistorySummary = getFakeHistorySummary()) {
    return shallowMount(HistoryMessages as object, {
        props: { history, currentUser },
        global: localVue,
    });
}

function getAnonymousUser(quotaPercent: number): AnonymousUser {
    return {
        isAnonymous: true,
        total_disk_usage: 0,
        nice_total_disk_usage: "0 bytes",
        quota_percent: quotaPercent,
    };
}

describe("HistoryMessages", () => {
    it.each([
        ["a registered user", getFakeRegisteredUser({ quota_percent: 100 }), getFakeHistorySummary()],
        ["an anonymous user", getAnonymousUser(100), { ...getFakeHistorySummary(), user_id: null }],
    ])("warns %s who reached their quota", (_description, user, history) => {
        const wrapper = mountHistoryMessages(user, history);

        expect(wrapper.find(OVER_QUOTA_MESSAGE).exists()).toBe(true);
    });

    it.each([
        { title: "warns a registered user whose usage exceeds the quota", usage: 1001, warns: true },
        { title: "doesn't warn a registered user whose usage equals the quota", usage: 1000, warns: false },
    ])("$title", ({ usage, warns }) => {
        // The server reports 100% in both cases: it caps the percentage
        const user = getFakeRegisteredUser({ total_disk_usage: usage, quota_bytes: 1000, quota_percent: 100 });

        const wrapper = mountHistoryMessages(user);

        expect(wrapper.find(OVER_QUOTA_MESSAGE).exists()).toBe(warns);
    });

    it("doesn't warn about the user's quota on someone else's history", () => {
        const user = { ...CURRENT_USER, quota_percent: 100 };
        const history = { ...getFakeHistorySummary(), user_id: "another_user_id" };

        const wrapper = mountHistoryMessages(user, history);

        expect(wrapper.find(MESSAGES).exists()).toBe(false);
    });

    it.each([
        ["below the quota", 99],
        ["without a quota", null],
    ])("shows no messages for a user %s", (_description, quotaPercent) => {
        const wrapper = mountHistoryMessages(getFakeRegisteredUser({ quota_percent: quotaPercent }));

        expect(wrapper.find(MESSAGES).exists()).toBe(false);
    });

    it.each([
        ["shows", "the current user", CURRENT_USER.id, true],
        ["hides", "someone else", "another_user_id", false],
    ])("%s messages for an archived history owned by %s", (_action, _owner, ownerId, expectedShown) => {
        const history = { ...getFakeHistorySummary({ archived: true }), user_id: ownerId };

        const wrapper = mountHistoryMessages(CURRENT_USER, history);

        expect(wrapper.find(MESSAGES).exists()).toBe(expectedShown);
    });
});
