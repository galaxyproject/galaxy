import { getFakeChatHistoryItem } from "@tests/test-data/chat";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import { useServerMock } from "@/api/client/__mocks__";

import { type ChatLocation, useChatStore } from "./chatStore";
import { setupTestPinia } from "./testUtils";

const { server, http } = useServerMock();
const deleteRequest = vi.fn();

function registerDeleteHandler() {
    server.use(
        http.put("/api/chat/exchanges/batch/delete", async ({ request, response }) => {
            deleteRequest(await request.json());
            return response(200).json({});
        }),
    );
}

vi.mock("@/composables/userLocalStorage", () => ({
    useUserLocalStorage: vi.fn((_key: string, initialValue: unknown) => ref(initialValue)),
}));

describe("chatStore", () => {
    beforeEach(() => {
        setupTestPinia();
        vi.clearAllMocks();
    });

    it("initializes with default state", () => {
        const store = useChatStore();
        expect(store.chatLocation).toBe("center");
        expect(store.chatVisible).toBe(false);
        expect(store.activeChatId).toBeNull();
    });

    describe("showChat", () => {
        it("sets visibility to true", () => {
            const store = useChatStore();
            store.showChat();
            expect(store.chatVisible).toBe(true);
        });

        it("sets chat ID when provided", () => {
            const store = useChatStore();
            store.showChat("chat-42");
            expect(store.chatVisible).toBe(true);
            expect(store.activeChatId).toBe("chat-42");
        });

        it("preserves existing chat ID when called without argument", () => {
            const store = useChatStore();
            store.setActiveChatId("existing-id");
            store.showChat();
            expect(store.activeChatId).toBe("existing-id");
        });

        it("clears chat ID when called with null", () => {
            const store = useChatStore();
            store.setActiveChatId("old-id");
            store.showChat(null);
            expect(store.chatVisible).toBe(true);
            expect(store.activeChatId).toBeNull();
        });
    });

    describe("hideChat", () => {
        it("sets visibility to false", () => {
            const store = useChatStore();
            store.showChat();
            store.hideChat();
            expect(store.chatVisible).toBe(false);
        });
    });

    describe("toggleChat", () => {
        it("flips visibility on", () => {
            const store = useChatStore();
            store.toggleChat();
            expect(store.chatVisible).toBe(true);
        });

        it("flips visibility off", () => {
            const store = useChatStore();
            store.showChat();
            store.toggleChat();
            expect(store.chatVisible).toBe(false);
        });
    });

    describe("setLocation", () => {
        it.each<{ from: ChatLocation; to: ChatLocation }>([
            { from: "center", to: "right" },
            { from: "right", to: "bottom" },
            { from: "bottom", to: "center" },
        ])("changes the chat location from $from to $to", ({ from, to }) => {
            const store = useChatStore();
            store.setLocation(from);
            store.setLocation(to);
            expect(store.chatLocation).toBe(to);
        });
    });

    describe("setActiveChatId", () => {
        it("sets and clears the active chat ID", () => {
            const store = useChatStore();
            store.setActiveChatId("abc");
            expect(store.activeChatId).toBe("abc");
            store.setActiveChatId(null);
            expect(store.activeChatId).toBeNull();
        });
    });

    describe("requestNewChat", () => {
        it("bumps the request counter so chat surfaces reset even when the id would not change", () => {
            const store = useChatStore();
            expect(store.newChatRequestCount).toBe(0);
            store.requestNewChat();
            expect(store.newChatRequestCount).toBe(1);
            store.requestNewChat();
            expect(store.newChatRequestCount).toBe(2);
        });

        it("clears the active chat id", () => {
            const store = useChatStore();
            store.setActiveChatId("abc");
            store.requestNewChat();
            expect(store.activeChatId).toBeNull();
        });
    });

    describe("deleteChats", () => {
        it("removes the given ids from history", () => {
            const store = useChatStore();
            store.chatHistory = ["a", "b", "c"].map((id) => getFakeChatHistoryItem({ id }));
            store.deleteChats(new Set(["a", "c"]));
            expect(store.chatHistory.map((item) => item.id)).toEqual(["b"]);
        });

        it("clears activeChatId when the open chat is among the deleted ids", () => {
            const store = useChatStore();
            store.chatHistory = ["a", "b"].map((id) => getFakeChatHistoryItem({ id }));
            store.setActiveChatId("a");
            store.deleteChats(new Set(["a"]));
            expect(store.activeChatId).toBeNull();
        });

        it("preserves activeChatId when the open chat is not deleted", () => {
            const store = useChatStore();
            store.chatHistory = ["a", "b"].map((id) => getFakeChatHistoryItem({ id }));
            store.setActiveChatId("b");
            store.deleteChats(new Set(["a"]));
            expect(store.activeChatId).toBe("b");
        });
    });

    describe("deleteChatsByIds", () => {
        it("deletes via the batch endpoint and drops the open chat if included", async () => {
            registerDeleteHandler();
            const store = useChatStore();
            store.chatHistory = ["a", "b", "c"].map((id) => getFakeChatHistoryItem({ id }));
            store.setActiveChatId("a");

            await store.deleteChatsByIds(new Set(["a", "b"]));

            expect(deleteRequest).toHaveBeenCalledExactlyOnceWith({ ids: ["a", "b"] });
            expect(store.chatHistory.map((item) => item.id)).toEqual(["c"]);
            expect(store.activeChatId).toBeNull();
        });

        it("does nothing for an empty set", async () => {
            registerDeleteHandler();
            const store = useChatStore();
            await store.deleteChatsByIds(new Set());
            expect(deleteRequest).not.toHaveBeenCalled();
        });
    });

    describe("computed panel states", () => {
        it("isRightPanelOpen is true only when right + visible", () => {
            const store = useChatStore();
            expect(store.isRightPanelOpen).toBe(false);

            store.setLocation("right");
            expect(store.isRightPanelOpen).toBe(false);

            store.showChat();
            expect(store.isRightPanelOpen).toBe(true);

            store.setLocation("bottom");
            expect(store.isRightPanelOpen).toBe(false);
        });

        it("isBottomPanelOpen is true only when bottom + visible", () => {
            const store = useChatStore();
            expect(store.isBottomPanelOpen).toBe(false);

            store.setLocation("bottom");
            store.showChat();
            expect(store.isBottomPanelOpen).toBe(true);

            store.hideChat();
            expect(store.isBottomPanelOpen).toBe(false);
        });

        it("isCenterMode reflects location regardless of visibility", () => {
            const store = useChatStore();
            expect(store.isCenterMode).toBe(true);

            store.showChat();
            expect(store.isCenterMode).toBe(true);

            store.setLocation("right");
            expect(store.isCenterMode).toBe(false);
        });
    });
});
