import MockAdapter from "axios-mock-adapter";
import axios from "axios";
import store from "store/index";

// response resource data
let nHistories = 3;
let currentHistory = 0;
const histories = {};
for (let i = 0; i < nHistories; i++) {
    histories[i] = { id: i, name: `default` };
}

// add secondary sets of histories
const buildDetails = (key, count = 0) => {
    const historyList = [];
    for (let i = 0; i < nHistories + count; i++) {
        const element = { id: i, name: `name_${key}` };
        element[key] = true;
        historyList.push(element);
    }
    return historyList;
};

// detail counter
const countDetails = (histories, key, value = true) => {
    let n = 0;
    histories.forEach((h) => {
        h[key] == value && n++;
    });
    return n;
};

describe("historyStore", () => {
    let axiosMock;

    beforeEach(() => {
        axiosMock = new MockAdapter(axios);
        axiosMock.onGet("/history/current_history_json").reply(() => {
            return [200, histories[currentHistory]];
        });
        axiosMock.onGet("/history/create_new_current").reply(() => {
            const id = nHistories++;
            return [200, { id: id }];
        });
        axiosMock.onGet("/history/set_as_current").reply((config) => {
            const payload = config.params;
            currentHistory = payload.id;
            return [200, histories[payload.id]];
        });
        axiosMock.onGet(/api\/histories\/./).reply((config) => {
            const historyId = config.url.charAt(config.url.length - 1);
            return [200, histories[historyId]];
        });
    });

    afterEach(() => {
        axiosMock.restore();
    });

    it("history lists", async () => {
        expect(store.getters["history/currentHistoryId"]).toBe(null);
        let hlist = store.getters["history/histories"];
        expect(hlist.length).toBe(0);
        await store.commit("history/setHistories", buildDetails("a", 5));
        hlist = store.getters["history/histories"];
        expect(countDetails(hlist, "a")).toBe(8);
        expect(countDetails(hlist, "b")).toBe(0);
        expect(countDetails(hlist, "name", "name_a")).toBe(8);
        await store.commit("history/setHistories", buildDetails("b"));
        hlist = store.getters["history/histories"];
        expect(countDetails(hlist, "a")).toBe(8);
        expect(countDetails(hlist, "b")).toBe(3);
        expect(countDetails(hlist, "name", "name_a")).toBe(5);
        expect(countDetails(hlist, "name", "name_b")).toBe(3);
    });

    it("store initialization", async () => {
        await store.dispatch("history/loadCurrentHistory");
        expect(store.getters["history/currentHistoryId"]).toBe(0);
        await store.dispatch("history/loadHistoryById", 1);
        await store.dispatch("history/loadHistoryById", 2);
        expect(store.getters["history/currentHistoryId"]).toBe(0);
        await store.dispatch("history/setCurrentHistory", 1);
        expect(store.getters["history/currentHistoryId"]).toBe(1);
        await store.dispatch("history/loadCurrentHistory");
        expect(store.getters["history/currentHistoryId"]).toBe(1);
        expect(store.getters["history/getHistoryById"](2).id).toBe(2);
        await store.dispatch("history/createNewHistory");
        expect(store.getters["history/currentHistoryId"]).toBe(3);
    });
});
