import { suppressDebugConsole } from "@tests/vitest/helpers";
import { createLocalVue, mount } from "@vue/test-utils";
import { createPinia, mapState } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import { useHistoryItemsStore } from "@/stores/historyItemsStore";
import { useHistoryStore } from "@/stores/historyStore";

import { watchHistoryOnce } from "./watchHistory";

const pinia = createPinia();
const { server, http } = useServerMock();

const testApp = {
    template: `<div/>`,
    computed: {
        ...mapState(useHistoryStore, ["currentHistoryId"]),
        ...mapState(useHistoryItemsStore, ["getHistoryItems"]),
    },
};

describe("watchHistory", () => {
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

    it("sets up the history and history item stores", async () => {
        server.use(
            http.untyped.get("/history/current_history_json", () => {
                return HttpResponse.json(historyData);
            }),
            http.untyped.get(/api\/histories\/history-id\/contents?.*/, () => {
                return HttpResponse.json(historyItems);
            }),
        );
        await watchHistoryOnce();
        expect(wrapper.vm.getHistoryItems("history-id", "").length).toBe(2);
        expect(wrapper.vm.getHistoryItems("history-id", "second")[0].hid).toBe(2);
        expect(wrapper.vm.getHistoryItems("history-id", "state:ok")[0].hid).toBe(1);
    });

    it("survives a failing request", async () => {
        suppressDebugConsole(); // we log that 500, totally expected, do not include it in test output

        // Stage 1: Initial successful load
        server.use(
            http.untyped.get("/history/current_history_json", () => {
                return HttpResponse.json(historyData);
            }),
            http.untyped.get(/api\/histories\/history-id\/contents?.*/, () => {
                return HttpResponse.json(historyItems);
            }),
        );

        await watchHistoryOnce();
        expect(wrapper.vm.currentHistoryId).toBe("history-id");
        expect(wrapper.vm.getHistoryItems("history-id", "").length).toBe(2);

        // Stage 2: Failing request
        server.resetHandlers();
        server.use(
            http.untyped.get("/history/current_history_json", () => {
                return new HttpResponse(null, { status: 500 });
            }),
        );

        try {
            await watchHistoryOnce();
        } catch (error) {
            expect(error.message).toContain("500");
        }

        // Stage 3: Recovery with updated data
        server.resetHandlers();
        server.use(
            http.untyped.get("/history/current_history_json", () => {
                return HttpResponse.json({ ...historyData, update_time: "1" });
            }),
            http.untyped.get(/api\/histories\/history-id\/contents?.*/, () => {
                return HttpResponse.json([
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
            }),
        );

        await watchHistoryOnce();
        // We should have received the update and have 3 items in the history
        expect(wrapper.vm.getHistoryItems("history-id", "").length).toBe(3);
    });
});
