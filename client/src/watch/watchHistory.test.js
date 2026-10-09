import { suppressDebugConsole } from "@tests/vitest/helpers";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";

const { server, http } = useServerMock();

function historyItem({ id, hid, name, state }) {
    return { id, hid, name, state, deleted: false, visible: true, history_id: "history-id" };
}

function serveHistory(updateTime, items) {
    server.use(
        http.untyped.get("/history/current_history_json", () => {
            return HttpResponse.json({ id: "history-id", update_time: updateTime });
        }),
        http.get("/api/histories/{history_id}/contents", ({ response }) => {
            return response.untyped(HttpResponse.json(items));
        }),
    );
}

describe("watchHistory", () => {
    let watchHistoryOnce;
    let historyStore;
    let historyItemsStore;
    let initialItems;

    beforeEach(async () => {
        // The watcher keeps its update-time cursor at module scope, independently of Pinia.
        // Import its stores from the same fresh registry so each scenario owns both caches.
        vi.resetModules();
        const [watcher, historyModule, itemsModule, { setupTestPinia }] = await Promise.all([
            import("./watchHistory"),
            import("@/stores/historyStore"),
            import("@/stores/historyItemsStore"),
            import("@/stores/testUtils"),
        ]);
        setupTestPinia();
        watchHistoryOnce = watcher.watchHistoryOnce;
        historyStore = historyModule.useHistoryStore();
        historyItemsStore = itemsModule.useHistoryItemsStore();
        historyStore.setHistories([{ id: "history-id" }]);
        historyStore.setCurrentHistoryId("history-id");
        initialItems = [
            historyItem({ id: "id-1", hid: 1, name: "first", state: "ok" }),
            historyItem({ id: "id-2", hid: 2, name: "second", state: "error" }),
        ];
    });

    it("loads history items and supports name and state filters", async () => {
        serveHistory("0", initialItems);

        await watchHistoryOnce();

        expect(historyItemsStore.getHistoryItems("history-id", "")).toHaveLength(2);
        expect(historyItemsStore.getHistoryItems("history-id", "second")[0].hid).toBe(2);
        expect(historyItemsStore.getHistoryItems("history-id", "state:ok")[0].hid).toBe(1);
    });

    it("retains loaded items after a failed request and merges the next successful update", async () => {
        suppressDebugConsole(); // The expected 500 response is logged by the HTTP client.
        serveHistory("0.1", initialItems);
        await watchHistoryOnce();
        expect(historyStore.currentHistoryId).toBe("history-id");
        expect(historyItemsStore.getHistoryItems("history-id", "")).toHaveLength(2);

        server.resetHandlers();
        server.use(
            http.untyped.get("/history/current_history_json", () => {
                return new HttpResponse(null, { status: 500 });
            }),
        );

        await expect(watchHistoryOnce()).rejects.toThrow("500");
        expect(historyItemsStore.getHistoryItems("history-id", "")).toHaveLength(2);

        server.resetHandlers();
        serveHistory("1", [historyItem({ id: "id-3", hid: 3, name: "third", state: "ok" })]);
        await watchHistoryOnce();

        expect(historyItemsStore.getHistoryItems("history-id", "")).toHaveLength(3);
    });
});
