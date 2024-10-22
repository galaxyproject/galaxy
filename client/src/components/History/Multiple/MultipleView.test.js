import { getFakeRegisteredUser } from "@tests/test-data";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia } from "pinia";
import { getLocalVue } from "tests/jest/helpers";

import { useServerMock } from "@/api/client/__mocks__";
import { useHistoryStore } from "@/stores/historyStore";
import { useUserStore } from "@/stores/userStore";

import MultipleView from "./MultipleView.vue";

const USER_ID = "test-user-id";
const FIRST_HISTORY_ID = "test-history-id-0";

const { server, http } = useServerMock();

const getFakeHistorySummaries = (num) => {
    return Array.from({ length: num }, (_, index) => ({
        id: `test-history-id-${index}`,
        name: `History-${index}`,
        tags: [],
        update_time: new Date().toISOString(),
    }));
};

describe("MultipleView", () => {
    async function setUpWrapper(count, currentHistoryId) {
        const fakeSummaries = getFakeHistorySummaries(count);

        server.use(
            http.get("/api/configuration", ({ response }) => {
                return response(200).json({});
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
            })
        );

        const wrapper = mount(MultipleView, {
            pinia: createPinia(),
            stubs: {
                HistoryPanel: true,
                icon: { template: "<div></div>" },
            },
            localVue: getLocalVue(),
        });

        const userStore = useUserStore();
        userStore.currentUser = getFakeRegisteredUser({ id: USER_ID });

        const historyStore = useHistoryStore();
        historyStore.setHistories(fakeSummaries);
        historyStore.setCurrentHistoryId(currentHistoryId);

        await flushPromises();

        return wrapper;
    }

    it("more than 4 histories should not show the current history", async () => {
        const count = 8;
        const currentHistoryId = FIRST_HISTORY_ID;

        // Set up UserHistories and wrapper
        const wrapper = await setUpWrapper(count, currentHistoryId);

        // Test: current (first) history should not be shown because only 4 latest are shown by default
        expect(wrapper.find("button[title='Current History']").exists()).toBeFalsy();

        expect(wrapper.find("button[title='Switch to this history']").exists()).toBeTruthy();

        expect(wrapper.find("div[title='Currently showing 4 most recently updated histories']").exists()).toBeTruthy();

        expect(wrapper.find("[data-description='open select histories modal']").exists()).toBeTruthy();
    });

    it("less than 4 histories should show the current history", async () => {
        const count = 3;
        const currentHistoryId = FIRST_HISTORY_ID;

        // Set up UserHistories and wrapper
        const wrapper = await setUpWrapper(count, currentHistoryId);

        // Test: current (first) history should be shown because only 4 latest are shown by default, and count = 3
        expect(wrapper.find("button[title='Current History']").exists()).toBeTruthy();
    });
});
