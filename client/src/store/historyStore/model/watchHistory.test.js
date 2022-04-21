import MockAdapter from "axios-mock-adapter";
import axios from "axios";
import { watchHistory } from "./watchHistory";
import store from "store/index";

describe("watchHistory", () => {
    let axiosMock;

    beforeEach(() => {
        axiosMock = new MockAdapter(axios);
        const historyData = {
            id: "history-id",
            update_time: "0",
        };
        axiosMock.onGet(`/history/current_history_json`).reply(200, historyData);
        const historyItems = [
            {
                id: "id-1",
                hid: 1,
                name: "first",
                state: "ok",
                deleted: false,
                visible: true,
            },
            {
                id: "id-2",
                hid: 2,
                name: "second",
                state: "error",
                deleted: false,
                visible: true,
            },
        ];
        axiosMock.onGet(/api\/histories\/history-id\/contents?.*/).reply(200, historyItems);
    });

    afterEach(() => {
        axiosMock.restore();
    });

    it("store initialization", async () => {
        expect(store.getters["history/currentHistoryId"]).toBe(null);
        await watchHistory();
        expect(store.getters["history/currentHistoryId"]).toBe("history-id");
        expect(store.getters["getHistoryItems"]({ historyId: "history-id", filterText: "" }).length).toBe(2);
        expect(store.getters["getHistoryItems"]({ historyId: "history-id", filterText: "second" })[0].hid).toBe(2);
        expect(store.getters["getHistoryItems"]({ historyId: "history-id", filterText: "state=ok" })[0].hid).toBe(1);
    });
});
