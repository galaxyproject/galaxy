import MockAdapter from "axios-mock-adapter";
import axios from "axios";
import { watchHistoryOnce } from "./watchHistory";
import { collectionElementsStore } from "store/historyStore/collectionElementsStore";
import { datasetStore } from "store/historyStore/datasetStore";
import { historyStore } from "store/historyStore/historyStore";
import { useHistoryItemsStore } from "stores/history/historyItemsStore";
import { createPinia, mapState } from "pinia";
import { mount, createLocalVue } from "@vue/test-utils";
import Vuex from "vuex";

const pinia = createPinia();

const testApp = {
    template: `<div/>`,
    computed: {
        ...mapState(useHistoryItemsStore, ["getHistoryItems"]),
        currentHistoryId() {
            return this.$store.getters["history/currentHistoryId"];
        },
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
        localVue.use(Vuex);
        useHistoryItemsStore(pinia);

        wrapper = mount(testApp, {
            store: new Vuex.Store({
                modules: {
                    collectionElements: collectionElementsStore,
                    dataset: datasetStore,
                    history: historyStore,
                },
            }),
            localVue,
            pinia,
        });
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
        await watchHistoryOnce(wrapper.vm.$store);
        expect(wrapper.vm.getHistoryItems("history-id", "").length).toBe(2);
        expect(wrapper.vm.getHistoryItems("history-id", "second")[0].hid).toBe(2);
        expect(wrapper.vm.getHistoryItems("history-id", "state:ok")[0].hid).toBe(1);
    });

    it("survives a failing request", async () => {
        // Setup a failing request, then update history content
        axiosMock
            .onGet(`/history/current_history_json`)
            .replyOnce(200, historyData)
            .onGet(/api\/histories\/history-id\/contents?.*/)
            .replyOnce(200, historyItems)
            .onGet(`/history/current_history_json`)
            .replyOnce(500);

        await watchHistoryOnce(wrapper.vm.$store);
        expect(wrapper.vm.currentHistoryId).toBe("history-id");
        expect(wrapper.vm.getHistoryItems("history-id", "").length).toBe(2);
        try {
            await watchHistoryOnce(wrapper.vm.$store);
        } catch (error) {
            console.log(error);
            expect(error.response.status).toBe(500);
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
        await watchHistoryOnce(wrapper.vm.$store);
        // We should have received the update and have 3 items in the history
        expect(wrapper.vm.getHistoryItems("history-id", "").length).toBe(3);
    });
});
