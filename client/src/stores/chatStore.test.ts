import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import { useChatStore } from "./chatStore";

vi.mock("@/composables/userLocalStorage", () => ({
    useUserLocalStorage: vi.fn((_key: string, initialValue: unknown) => ref(initialValue)),
}));

describe("chatStore", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
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
        it("changes the chat location", () => {
            const store = useChatStore();
            store.setLocation("right");
            expect(store.chatLocation).toBe("right");
            store.setLocation("bottom");
            expect(store.chatLocation).toBe("bottom");
            store.setLocation("center");
            expect(store.chatLocation).toBe("center");
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
