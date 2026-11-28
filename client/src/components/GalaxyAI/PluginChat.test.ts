import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount, type VueWrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useChatStore } from "@/stores/chatStore";
import { useConfigStore } from "@/stores/configurationStore";
import { useUserStore } from "@/stores/userStore";

import PluginChat from "./PluginChat.vue";
import GAlert from "@/components/BaseComponents/GAlert.vue";

const mockReplace = vi.fn();
const mockRoute = { path: "/galaxyai/new" };

vi.mock("vue-router", () => ({
    useRoute: () => mockRoute,
    useRouter: () => ({ replace: mockReplace, push: vi.fn() }),
}));
vi.mock("@/api/client", () => ({
    GalaxyApi: () => ({
        GET: vi.fn((path: string) => (path === "/api/configuration" ? new Promise(() => {}) : { data: [] })),
    }),
}));

const localVue = getLocalVue();

let mounted: VueWrapper[] = [];
afterEach(() => {
    mounted.forEach((wrapper) => wrapper.unmount());
    mounted = [];
    mockReplace.mockClear();
    vi.unstubAllGlobals();
});

function mountPlace(
    propsData: Record<string, unknown>,
    before: (store: ReturnType<typeof useChatStore>) => void = () => {},
) {
    const pinia = createPinia();
    setActivePinia(pinia);
    useConfigStore().setConfiguration({ ai_chat_plugin: "fixture" });
    useUserStore().currentUser = { id: "u1", email: "u1@example.org" } as never;
    const store = useChatStore();
    before(store);
    mounted.push(shallowMount(PluginChat as object, { localVue, pinia, propsData }));
    return store;
}

describe("PluginChat in the center", () => {
    it("opens the saved chat the address names", () => {
        const store = mountPlace({ source: "center", exchangeId: "a1" });
        expect(store.chatCommands).toEqual([{ type: "open", exchange_id: "a1" }]);
    });

    it("leaves the plugin its own chat for a new chat or no chat", () => {
        expect(mountPlace({ source: "center", exchangeId: "new" }).chatCommands).toEqual([]);
        expect(mountPlace({ source: "center" }).chatCommands).toEqual([]);
    });

    it("asks a question handed over in the address once", () => {
        const store = mountPlace({ source: "center", exchangeId: "new", initialQuestion: "What is in my history?" });
        expect(store.chatCommands).toEqual([{ type: "ask", question: "What is in my history?" }]);
        expect(mockReplace).toHaveBeenCalledWith({ path: "/galaxyai/new", query: {} });
    });

    it("sends the address back to the chat shown when the user keeps its unsaved changes", () => {
        const confirm = vi.fn(() => false);
        vi.stubGlobal("confirm", confirm);
        const unsavedOn = (store: ReturnType<typeof useChatStore>) => {
            store.pluginShows("a1");
            store.unsaved = true;
        };
        mountPlace({ source: "center", exchangeId: "b2" }, unsavedOn);
        expect(mockReplace).toHaveBeenLastCalledWith("/galaxyai/a1");
        mountPlace({ source: "center", exchangeId: "new", initialQuestion: "Count my reads" }, unsavedOn);
        expect(mockReplace).toHaveBeenLastCalledWith("/galaxyai/a1");
        expect(confirm).toHaveBeenCalledTimes(2);
    });

    it("follows the chat the plugin reports in the address", async () => {
        const store = mountPlace({ source: "center" });
        store.pluginShows("c1");
        await flushPromises();
        expect(mockReplace).toHaveBeenLastCalledWith("/galaxyai/c1");
    });
});

describe("PluginChat in a dock", () => {
    it("leaves the address alone", async () => {
        const store = mountPlace({ source: "docked", exchangeId: "a1" });
        store.pluginShows("c1");
        await flushPromises();
        expect(store.chatCommands).toEqual([]);
        expect(mockReplace).not.toHaveBeenCalled();
    });

    it("is where the plugin shows while mounted, unless a newer place took over", () => {
        const store = mountPlace({ source: "panel" });
        const first = mounted[0]!.find(".plugin-chat-body").element;
        expect(store.chatSlot).toBe(first);
        const second = shallowMount(PluginChat as object, { localVue, propsData: { source: "docked" } });
        expect(store.chatSlot).toBe(second.find(".plugin-chat-body").element);
        mounted[0]!.unmount();
        mounted = [];
        expect(store.chatSlot).toBe(second.find(".plugin-chat-body").element);
        second.unmount();
        expect(store.chatSlot).toBeNull();
    });

    it("says when the plugin did not start", async () => {
        const store = mountPlace({ source: "panel" });
        expect(mounted[0]!.findComponent(GAlert).exists()).toBe(false);
        store.agentSilent();
        await flushPromises();
        expect(mounted[0]!.findComponent(GAlert).text()).toContain("The AI chat did not start");
    });
});
