import { getFakeHistorySummary, getFakeQuotaUsageData, getFakeRegisteredUser, getFakeStorage } from "@tests/test-data";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia, setActivePinia } from "pinia";
import { describe, expect, it } from "vitest";

import type { AnonymousUser, AnyUser, HistorySummary } from "@/api";
import { useServerMock } from "@/api/client/__mocks__";
import { toQuotaUsage, type UserQuotaUsageData } from "@/components/User/DiskUsage/Quota/model/QuotaUsage";
import { useQuotaUsageStore } from "@/stores/quotaUsageStore";

import HistoryMessages from "./HistoryMessages.vue";

const localVue = getLocalVue();
const { server, http } = useServerMock();

const MESSAGES = "[data-description='history messages']";
const OVER_QUOTA_MESSAGE = "[data-description='over quota message']";
const OTHER_SOURCES_OVER_QUOTA_MESSAGE = "[data-description='other sources over quota message']";

const CURRENT_USER = getFakeRegisteredUser({ id: "current_user_id" });

function mountHistoryMessages(
    currentUser: AnyUser,
    history: HistorySummary = getFakeHistorySummary(),
    quotaUsages: UserQuotaUsageData[] = [],
) {
    const pinia = createPinia();
    setActivePinia(pinia);
    useQuotaUsageStore().quotaUsages = quotaUsages.map(toQuotaUsage);
    return shallowMount(HistoryMessages as object, {
        props: { history, currentUser },
        global: withPlugins(localVue, pinia),
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

    it("doesn't warn about the user's quotas on someone else's history", () => {
        const user = { ...CURRENT_USER, quota_percent: 100 };
        const history = { ...getFakeHistorySummary(), user_id: "another_user_id" };

        const wrapper = mountHistoryMessages(user, history, [getFakeQuotaUsageData("scratch", 1001)]);

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

    it("names the other storage sources whose quota the user exceeded after their storages", async () => {
        server.use(
            http.get("/api/object_stores", ({ response }) =>
                response(200).json([getFakeStorage("scratch", "Scratch Storage", { source: "scratch" })]),
            ),
        );
        const usages = [
            getFakeQuotaUsageData(null, 200),
            getFakeQuotaUsageData("scratch", 1001),
            getFakeQuotaUsageData("archive", 1500),
        ];

        const wrapper = mountHistoryMessages(getFakeRegisteredUser({ quota_percent: 20 }), undefined, usages);

        expect(wrapper.find(OVER_QUOTA_MESSAGE).exists()).toBe(false);
        await flushPromises();

        // No storage uses the archive source, so it keeps its label
        expect(wrapper.find(OTHER_SOURCES_OVER_QUOTA_MESSAGE).text()).toContain("Scratch Storage, archive");
    });

    it("shows no messages while the other storage sources don't exceed their quota", () => {
        const usages = [getFakeQuotaUsageData(null, 200), getFakeQuotaUsageData("scratch", 1000, 1000)];

        const wrapper = mountHistoryMessages(getFakeRegisteredUser({ quota_percent: 20 }), undefined, usages);

        expect(wrapper.find(MESSAGES).exists()).toBe(false);
    });
});
