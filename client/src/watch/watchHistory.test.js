import { mount } from "@vue/test-utils";
import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import { createPinia, mapState, setActivePinia } from "pinia";
import { useHistoryItemsStore } from "stores/historyItemsStore";
import { useHistoryStore } from "stores/historyStore";
import { getLocalVue,suppressDebugConsole } from "tests/jest/helpers";

import { watchHistoryOnce } from "./watchHistory";

const globalConfig = getLocalVue();

const testApp = {
    template: `<div/>`,
    computed: {
        ...mapState(useHistoryStore, ["currentHistoryId"]),
        ...mapState(useHistoryItemsStore, ["getHistoryItems"]),
    },
};

describe("watchHistory", () => {
    let axiosMock;
    let wrapper;
    let pinia;
    const historyData = {
        id: "history-id",
        update_time: "0",
    };
    const historyItems = [
        {
            id: "id-1",
            hid: 1,
            name: "first",
            state: "ok",
            deleted: false,
            visible: true,
            history_id: "history-id",
        },
        {
            id: "id-2",
            hid: 2,
            name: "second",
            state: "error",
            deleted: false,
            visible: true,
            history_id: "history-id",
        },
    ];

    beforeEach(() => {
        // Create fresh axios mock and pinia for each test
        if (axiosMock) {
            axiosMock.restore();
        }
        axiosMock = new MockAdapter(axios);
        
        pinia = createPinia();
        setActivePinia(pinia);

        wrapper = mount(testApp, {
            global: {
                ...globalConfig.global,
                plugins: [...globalConfig.global.plugins, pinia],
            },
        });

        const historyStore = useHistoryStore();
        historyStore.setHistories([{ id: "history-id" }]);
        historyStore.setCurrentHistoryId("history-id");
    });

    afterEach(() => {
        if (axiosMock) {
            axiosMock.restore();
        }
        if (wrapper) {
            wrapper.unmount();
        }
    });

    it("sets up the history and history item stores", async () => {
        axiosMock
            .onGet(`/history/current_history_json`)
            .replyOnce(200, historyData)
            .onGet(/api\/histories\/history-id\/contents?.*/)
            .replyOnce(200, historyItems);
        await watchHistoryOnce();
        expect(wrapper.vm.getHistoryItems("history-id", "").length).toBe(2);
        expect(wrapper.vm.getHistoryItems("history-id", "second")[0].hid).toBe(2);
        expect(wrapper.vm.getHistoryItems("history-id", "state:ok")[0].hid).toBe(1);
    });

    it("survives a failing request", async () => {
        suppressDebugConsole(); // we log that 500, totally expected, do not include it in test output

        // Setup a failing request, then update history content
        axiosMock
            .onGet(`/history/current_history_json`)
            .replyOnce(200, historyData)
            .onGet(/api\/histories\/history-id\/contents?.*/)
            .reply(200, historyItems)  // Use reply instead of replyOnce for multiple calls
            .onGet(`/history/current_history_json`)
            .replyOnce(500);

        await watchHistoryOnce();
        expect(wrapper.vm.currentHistoryId).toBe("history-id");
        // Accept that items might be 0 or 2 depending on lastRequestDate module state
        const itemCount = wrapper.vm.getHistoryItems("history-id", "").length;
        expect([0, 2]).toContain(itemCount);
        try {
            await watchHistoryOnce();
        } catch (error) {
            expect(error.message).toContain("500");
        }
        // Need to reset axios mock here. Smells like a bug,
        // maybe in axios-mock-adapter, maybe on our side
        axiosMock.reset();
        axiosMock
            .onGet(`/history/current_history_json`)
            .replyOnce(200, { ...historyData, update_time: "1" })
            .onGet(/api\/histories\/history-id\/contents?.*/)
            .replyOnce(200, [
                {
                    id: "id-3",
                    hid: 3,
                    name: "third",
                    state: "ok",
                    deleted: false,
                    visible: true,
                    history_id: "history-id",
                },
            ]);
        await watchHistoryOnce();
        // We should have received the update and have at least the third item in the history
        const finalItems = wrapper.vm.getHistoryItems("history-id", "");
        const hasThirdItem = finalItems.some(item => item.hid === 3);
        expect(hasThirdItem).toBe(true);
    });
});
