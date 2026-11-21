import flushPromises from "flush-promises";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import { Toast } from "@/composables/toast";
import { useConfigStore } from "@/stores/configurationStore";
import { useUserStore } from "@/stores/userStore";

import { useChatStore } from "./chatStore";

const { mockConfig, historyFails } = vi.hoisted(() => ({
    mockConfig: { value: {} as Record<string, unknown> },
    historyFails: { value: false },
}));

vi.mock("@/api/client", () => ({
    GalaxyApi: () => ({
        GET: vi.fn(async (path: string) =>
            path === "/api/chat/history" && historyFails.value
                ? { error: { err_msg: "History unavailable" } }
                : { data: path === "/api/configuration" ? mockConfig.value : [] },
        ),
    }),
}));

vi.mock("@/composables/userLocalStorage", () => ({
    useUserLocalStorage: vi.fn((key: string, initialValue: unknown) =>
        ref(key === "active-chat-id" ? "native-chat" : initialValue),
    ),
}));

const SIGNED_IN = { id: "u1", email: "u1@example.org" };

function storeOf(config: Record<string, unknown> | null, user: object | null = SIGNED_IN) {
    setActivePinia(createPinia());
    if (config) {
        mockConfig.value = config;
        useConfigStore().setConfiguration(config);
    }
    useUserStore().currentUser = user as never;
    return useChatStore();
}

function storeWith(plugin: string | null) {
    return storeOf({ ai_chat_plugin: plugin });
}

afterEach(() => {
    historyFails.value = false;
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
});

describe("the chat store with a chat plugin", () => {
    let store: ReturnType<typeof useChatStore>;
    beforeEach(() => {
        store = storeWith("fixture");
    });

    it("names the plugin and shows the chat the plugin reports", () => {
        expect(store.chatPlugin).toBe("fixture");
        expect(store.activeChatId).toBeNull();
        store.pluginShows("a1");
        expect(store.activeChatId).toBe("a1");
        store.setActiveChatId("b2");
        store.showChat("c3");
        expect(store.activeChatId).toBe("a1");
    });

    it("holds the commands in order until the plugin is ready", () => {
        store.openChat("a1");
        store.askChat("Count my reads");
        store.askChat("Count my reads");
        expect(store.takeCommands()).toEqual([]);
        store.agentState = "ready";
        expect(store.takeCommands()).toEqual([
            { type: "open", exchange_id: "a1" },
            { type: "ask", question: "Count my reads" },
            { type: "ask", question: "Count my reads" },
        ]);
        expect(store.takeCommands()).toEqual([]);
    });

    it("leaves the chat the plugin shows, unless a pending command replaces it", () => {
        store.pluginShows("a1");
        expect(store.openChat("a1")).toBe(true);
        expect(store.chatCommands).toEqual([]);
        store.chatCommands.push({ type: "open", exchange_id: "b2" });
        store.openChat("a1");
        expect(store.chatCommands).toEqual([
            { type: "open", exchange_id: "b2" },
            { type: "open", exchange_id: "a1" },
        ]);
    });

    it("asks before replacing an unsaved conversation, and sends nothing if declined", () => {
        const confirm = vi.fn(() => false);
        vi.stubGlobal("confirm", confirm);
        store.unsaved = true;
        expect(store.openChat("b2")).toBe(false);
        expect(store.askChat("Count my reads")).toBe(false);
        expect(store.chatCommands).toEqual([]);
        confirm.mockReturnValue(true);
        expect(store.askChat("Count my reads")).toBe(true);
        expect(store.chatCommands).toEqual([{ type: "ask", question: "Count my reads" }]);
    });

    it("says when the plugin did not start, and not once it is ready", () => {
        store.agentSilent();
        expect(store.agentState).toBe("failed");
        store.agentState = "ready";
        store.agentSilent();
        expect(store.agentState).toBe("ready");
    });

    it("says when the chat list cannot be refreshed for a chat the plugin saved", async () => {
        historyFails.value = true;
        const toast = vi.spyOn(Toast, "error").mockImplementation(() => undefined as never);
        store.pluginShows("a1");
        await flushPromises();
        expect(toast).toHaveBeenCalledWith("History unavailable", "Failed to load chat history");
    });

    it("lists every chat, also in a notebook", async () => {
        await store.loadHistory("page1");
        expect(store.chatHistory).toEqual([]);
    });
});

describe("the chat store without a chat plugin", () => {
    it("keeps Galaxy's own chat state", () => {
        const store = storeWith(null);
        expect(store.chatPlugin).toBeNull();
        expect(store.activeChatId).toBe("native-chat");
        expect(store.openChat("b2")).toBe(true);
        expect(store.activeChatId).toBe("b2");
        expect(store.chatCommands).toEqual([]);
    });
});

describe("which chat the store hosts", () => {
    it("names the configured plugin for a signed-in user, with or without Galaxy's own AI", () => {
        expect(storeOf({ ai_chat_plugin: "fixture" }).chatPlugin).toBe("fixture");
        expect(storeOf({ ai_chat_plugin: "fixture", llm_api_configured: true }).chatPlugin).toBe("fixture");
    });

    it("chooses Galaxy's own chat without a plugin, or for an anonymous user", () => {
        expect(storeOf({ llm_api_configured: true }).chatPlugin).toBeNull();
        expect(storeOf({ ai_chat_plugin: "fixture" }, { total_disk_usage: 0 }).chatPlugin).toBeNull();
    });

    it("waits for the configuration, and for the user only when a plugin is configured", () => {
        expect(storeOf(null).chatPlugin).toBeUndefined();
        expect(storeOf({ ai_chat_plugin: "fixture" }, null).chatPlugin).toBeUndefined();
        expect(storeOf({ llm_api_configured: true }, null).chatPlugin).toBeNull();
    });
});
