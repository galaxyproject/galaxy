import { getFakeHistorySummary, getFakeRegisteredUser } from "@tests/test-data";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { setupMockConfig } from "@tests/vitest/mockConfig";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia } from "pinia";
import { afterEach, describe, expect, it } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";
import { useHistoryStore } from "@/stores/historyStore";
import { useUserStore } from "@/stores/userStore";

import MultipleView from "./MultipleView.vue";

const USER_ID = "test-user-id";
const FIRST_HISTORY_ID = "test-history-id-0";

setupMockConfig({});

const { server, http } = useServerMock();

enableAutoUnmount(afterEach);

const getFakeHistorySummaries = (num) => {
    return Array.from({ length: num }, (_, index) =>
        getFakeHistorySummary({
            id: `test-history-id-${index}`,
            name: `History-${index}`,
            tags: [],
            update_time: `2026-01-01T00:00:${String(index).padStart(2, "0")}`,
        }),
    );
};

describe("MultipleView", () => {
    async function setUpWrapper(count, currentHistoryId) {
        const fakeSummaries = getFakeHistorySummaries(count);

        server.use(
            http.get("/api/object_stores", ({ response }) => {
                return response(200).json([]);
            }),

            http.get("/api/histories/{history_id}", ({ response, params }) => {
                const { history_id } = params;
                const summary = fakeSummaries.find((s) => s.id === history_id);
                if (!summary) {
                    return response("4XX").json({ err_msg: "History not found", err_code: 404 }, { status: 404 });
                }
                return response(200).json(summary);
            }),

            http.get("/api/histories/{history_id}/contents", ({ response }) => {
                return response(200).json({
                    stats: { total_matches: 0 },
                    contents: [],
                });
            }),
        );

        const pinia = createPinia();
        const localVue = getLocalVue();
        const wrapper = mount(MultipleView, {
            global: {
                ...withPlugins(localVue, pinia),
                stubs: {
                    HistoryPanel: true,
                    icon: { template: "<div></div>" },
                    "router-link": { template: "<a><slot /></a>", props: ["to"] },
                },
            },
        });

        const userStore = useUserStore();
        userStore.currentUser = getFakeRegisteredUser({ id: USER_ID });

        const historyStore = useHistoryStore();
        historyStore.setHistories(fakeSummaries);
        historyStore.setCurrentHistoryId(currentHistoryId);

        await flushPromises();

        return wrapper;
    }

    it("hides the oldest current history when only four of eight histories are displayed", async () => {
        const count = 8;
        const currentHistoryId = FIRST_HISTORY_ID;

        const wrapper = await setUpWrapper(count, currentHistoryId);

        expect(wrapper.find("button[title='Current History']").exists()).toBe(false);

        expect(wrapper.find("button[title='Switch to this history']").exists()).toBe(true);

        expect(wrapper.find("div[title='Currently showing 4 most recently updated histories']").exists()).toBe(true);

        expect(wrapper.find("[data-description='open select histories modal']").exists()).toBe(true);
    });

    it("shows the current history when all three histories fit in the display", async () => {
        const count = 3;
        const currentHistoryId = FIRST_HISTORY_ID;

        const wrapper = await setUpWrapper(count, currentHistoryId);

        expect(wrapper.find("button[title='Current History']").exists()).toBe(true);
    });

    it("load more button is shown when histories exceed the display limit", async () => {
        const wrapper = await setUpWrapper(8, FIRST_HISTORY_ID);
        expect(wrapper.find(".load-more-picker").exists()).toBe(true);
    });

    it("load more button is hidden when all histories fit within the display limit", async () => {
        const wrapper = await setUpWrapper(3, FIRST_HISTORY_ID);
        expect(wrapper.find(".load-more-picker").exists()).toBe(false);
    });

    it("clicking load more expands displayed histories and hides the button when all are shown", async () => {
        const wrapper = await setUpWrapper(8, FIRST_HISTORY_ID);

        expect(wrapper.find(".load-more-picker").exists()).toBe(true);
        expect(wrapper.find("div[title='Currently showing 4 most recently updated histories']").exists()).toBe(true);

        await wrapper.find(".load-more-picker").trigger("click");
        await flushPromises();

        expect(wrapper.find(".load-more-picker").exists()).toBe(false);
        expect(wrapper.find("div[title='Currently showing 8 most recently updated histories']").exists()).toBe(true);
    });

    it("clicking load more multiple times progressively shows more histories", async () => {
        const wrapper = await setUpWrapper(12, FIRST_HISTORY_ID);

        expect(wrapper.find("div[title='Currently showing 4 most recently updated histories']").exists()).toBe(true);

        await wrapper.find(".load-more-picker").trigger("click");
        await flushPromises();
        expect(wrapper.find(".load-more-picker").exists()).toBe(true);
        expect(wrapper.find("div[title='Currently showing 8 most recently updated histories']").exists()).toBe(true);

        await wrapper.find(".load-more-picker").trigger("click");
        await flushPromises();
        expect(wrapper.find(".load-more-picker").exists()).toBe(false);
        expect(wrapper.find("div[title='Currently showing 12 most recently updated histories']").exists()).toBe(true);
    });
});
