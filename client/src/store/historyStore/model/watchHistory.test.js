import { createLocalVue, mount } from "@vue/test-utils";
import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import { createPinia, mapState } from "pinia";
import { useHistoryItemsStore } from "stores/historyItemsStore";
import { useHistoryStore } from "stores/historyStore";
import { suppressDebugConsole } from "tests/jest/helpers";

import { watchHistoryOnce } from "./watchHistory";

const pinia = createPinia();

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
        axiosMock = new MockAdapter(axios);
        const localVue = createLocalVue();
        useHistoryItemsStore(pinia);

        wrapper = mount(testApp, {
            localVue,
            pinia,
        });

        const historyStore = useHistoryStore();
        historyStore.setHistories([{ id: "history-id" }]);
        historyStore.setCurrentHistoryId("history-id");
    });

    afterEach(() => {
        axiosMock.reset();
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
            .replyOnce(200, historyItems)
            .onGet(`/history/current_history_json`)
            .replyOnce(500);

        await watchHistoryOnce();
        expect(wrapper.vm.currentHistoryId).toBe("history-id");
        expect(wrapper.vm.getHistoryItems("history-id", "").length).toBe(2);
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
        // We should have received the update and have 3 items in the history
        expect(wrapper.vm.getHistoryItems("history-id", "").length).toBe(3);
    });
});
