import { getLocalVue } from "@tests/vitest/helpers";
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { describe, expect, it, vi } from "vitest";
import { defineComponent, h } from "vue";

import { useChatStore } from "@/stores/chatStore";
import { useConfigStore } from "@/stores/configurationStore";
import { useUserStore } from "@/stores/userStore";

import ChatHistoryPanel from "./ChatHistoryPanel.vue";

const mockPush = vi.fn();

vi.mock("vue-router", () => ({
    useRoute: () => ({ path: "/", params: {} }),
    useRouter: () => ({ push: mockPush }),
}));
vi.mock("@/composables/useActiveContext", () => ({ useActiveContext: () => ({ activeContext: { value: null } }) }));
vi.mock("@/api/client", () => ({
    GalaxyApi: () => ({
        GET: vi.fn((path: string) => (path === "/api/configuration" ? new Promise(() => {}) : { data: CHATS })),
    }),
}));

const CHATS = [
    { id: "a1", query: "Plot the counts", response: "Done", agent_type: "olit" },
    { id: "g1", query: "What is a BAM file?", response: "A format", agent_type: "router" },
];

const localVue = getLocalVue();

function mountPanel(plugin: string | null) {
    const pinia = createPinia();
    setActivePinia(pinia);
    useConfigStore().setConfiguration({ ai_chat_plugin: plugin, llm_api_configured: true });
    useUserStore().currentUser = { id: "u1", email: "u1@example.org" } as never;
    const store = useChatStore();
    store.setLocation("right");
    const wrapper = mount(ChatHistoryPanel as object, {
        localVue,
        pinia,
        stubs: {
            ActivityPanel: defineComponent({
                setup(_, { slots }) {
                    return () => h("div", [slots["header-buttons"]?.(), slots.default?.()]);
                },
            }),
            ScrollList: defineComponent({
                props: { propItems: { type: Array, default: () => [] } },
                setup(props, { slots }) {
                    return () =>
                        h(
                            "div",
                            props.propItems.map((item, index) => slots.item?.({ item, index })),
                        );
                },
            }),
            ChatModeSelector: true,
            UtcDate: true,
            FontAwesomeIcon: true,
        },
    });
    return { wrapper, store };
}

describe("ChatHistoryPanel", () => {
    it("lists every saved chat in both modes", async () => {
        for (const plugin of ["fixture", null]) {
            const { wrapper } = mountPanel(plugin);
            await flushPromises();
            expect(wrapper.findAll(".history-query").map((query) => query.text())).toEqual([
                "Plot the counts",
                "What is a BAM file?",
            ]);
        }
    });

    it("offers a new chat only in Galaxy's own chat", async () => {
        expect(mountPanel(null).wrapper.find("[title='New Chat']").exists()).toBe(true);
        expect(mountPanel("fixture").wrapper.find("[title='New Chat']").exists()).toBe(false);
    });

    it("opens a saved chat in the plugin when docked", async () => {
        const { wrapper, store } = mountPanel("fixture");
        await flushPromises();
        await wrapper.find(".chat-history-item").trigger("click");
        expect(store.chatCommands).toEqual([{ type: "open", exchange_id: "a1" }]);
        expect(store.chatVisible).toBe(true);
    });

    it("shows a saved chat in Galaxy's own chat when docked", async () => {
        const { wrapper, store } = mountPanel(null);
        await flushPromises();
        await wrapper.findAll(".chat-history-item")[1]!.trigger("click");
        expect(store.activeChatId).toBe("g1");
        expect(store.chatCommands).toEqual([]);
        expect(store.chatVisible).toBe(true);
    });
});
