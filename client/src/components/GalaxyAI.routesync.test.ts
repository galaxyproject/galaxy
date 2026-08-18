import { getLocalVue } from "@tests/vitest/helpers";
import { mount, type Wrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import { useChatStore } from "@/stores/chatStore";

import GalaxyAI from "./GalaxyAI.vue";

const { mockGet, mockPost, mockPut, routerMock, ChatMessageCellStub, ChatInputStub } = vi.hoisted(() => ({
    mockGet: vi.fn(),
    mockPost: vi.fn(),
    mockPut: vi.fn(),
    routerMock: { push: vi.fn(), replace: vi.fn() },
    // render functions because the test environment uses the runtime-only Vue build
    ChatMessageCellStub: {
        name: "ChatMessageCellStub",
        props: ["message"],
        render(this: { message: { content: string } }, h: (...args: unknown[]) => unknown) {
            return h("div", { class: "chat-message-stub" }, [this.message.content]);
        },
    },
    ChatInputStub: {
        name: "ChatInputStub",
        props: ["value", "busy"],
        render(h: (...args: unknown[]) => unknown) {
            return h("input", { class: "chat-input-stub" });
        },
    },
}));

vi.mock("@/api", () => ({
    GalaxyApi: () => ({ GET: mockGet, POST: mockPost, PUT: mockPut, DELETE: vi.fn() }),
}));

vi.mock("@/api/client", () => ({
    GalaxyApi: () => ({ GET: mockGet, POST: mockPost, PUT: mockPut, DELETE: vi.fn() }),
}));

// Center (route) mode: the component keeps the /galaxyai/<exchange> path in sync.
vi.mock("vue-router/composables", () => ({
    useRoute: () => ({ path: "/galaxyai", params: {}, query: {} }),
    useRouter: () => routerMock,
}));

vi.mock("@/app", () => ({
    getGalaxyInstance: () => ({ frame: { add: vi.fn() } }),
}));

// Child components are referenced directly from setup scope, so the test-utils
// `stubs` option cannot replace them — mock the modules instead.
vi.mock("@/components/GalaxyAI/ChatMessageCell.vue", () => ({ default: ChatMessageCellStub }));
vi.mock("@/components/GalaxyAI/ChatInput.vue", () => ({ default: ChatInputStub }));

vi.mock("@/composables/useActiveContext", () => ({
    useActiveContext: () => ({ activeContext: ref(null), contextLabel: ref("") }),
}));

vi.mock("@/composables/agentActions", () => ({
    useAgentActions: () => ({ processingAction: ref(false), handleAction: vi.fn() }),
}));

vi.mock("@/composables/confirmDialog", () => ({
    useConfirmDialog: () => ({ confirm: vi.fn() }),
}));

vi.mock("@/composables/markdown", () => ({
    useMarkdown: () => ({ renderMarkdown: (content: string) => content }),
}));

vi.mock("@/composables/toast", () => ({
    useToast: () => ({ error: vi.fn(), success: vi.fn(), warning: vi.fn(), info: vi.fn() }),
}));

vi.mock("@/composables/useEntityMentions", () => ({
    MENTION_PATTERN_SOURCE: "@(dataset|history):(\\S+)",
    parseMentions: () => [],
    resolveMentions: () => [],
    buildEntityContext: () => null,
}));

vi.mock("@/composables/userLocalStorage", () => ({
    useUserLocalStorage: vi.fn((_key: string, initialValue: unknown) => ref(initialValue)),
}));

const localVue = getLocalVue();

// jsdom does not implement Element.scrollTo
window.HTMLElement.prototype.scrollTo = vi.fn();

function mountChat() {
    const pinia = createPinia();
    setActivePinia(pinia);
    const wrapper = mount(GalaxyAI as object, {
        localVue,
        pinia,
        propsData: { panel: true },
        stubs: { FontAwesomeIcon: true, BSkeleton: true },
    });
    const chatStore = useChatStore();
    return { wrapper, chatStore };
}

function messageTexts(wrapper: Wrapper<Vue>) {
    return wrapper.findAll(".chat-message-stub").wrappers.map((w) => w.text());
}

async function sendMessage(wrapper: Wrapper<Vue>, text: string) {
    const input = wrapper.findComponent(ChatInputStub);
    input.vm.$emit("input", text);
    await wrapper.vm.$nextTick();
    input.vm.$emit("submit");
    await flushPromises();
}

function deferredResponse() {
    let resolve!: (value: unknown) => void;
    const promise = new Promise((r) => {
        resolve = r;
    });
    return { promise, resolve };
}

describe("GalaxyAI route sync", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockGet.mockResolvedValue({ data: [], error: undefined });
    });

    async function mountFreshChat() {
        const mounted = mountChat();
        await flushPromises();
        // the fresh conversation the component starts with already synced the route
        routerMock.replace.mockClear();
        return mounted;
    }

    it("routes to the saved exchange once its history load finishes", async () => {
        mockPost.mockResolvedValue({
            data: { response: "Here you go", exchange_id: "exchange-123" },
            error: undefined,
        });
        const { wrapper } = await mountFreshChat();

        await sendMessage(wrapper, "find me a mapper");

        expect(routerMock.replace).toHaveBeenCalledWith("/galaxyai/exchange-123");
    });

    it("does not route back to the previous exchange when a new chat is started", async () => {
        mockPost.mockResolvedValue({
            data: { response: "Here you go", exchange_id: "exchange-123" },
            error: undefined,
        });
        const { wrapper, chatStore } = await mountFreshChat();

        // the history refresh triggered by the new exchange id — left in flight
        const historyLoad = deferredResponse();
        mockGet.mockReturnValueOnce(historyLoad.promise);

        await sendMessage(wrapper, "find me a mapper");
        // the route can only be updated once that refresh settles
        expect(routerMock.replace).not.toHaveBeenCalled();

        chatStore.requestNewChat();
        await flushPromises();
        expect(routerMock.replace).toHaveBeenCalledWith("/galaxyai/new");
        expect(messageTexts(wrapper)).toHaveLength(1);

        historyLoad.resolve({ data: [], error: undefined });
        await flushPromises();

        expect(routerMock.replace).not.toHaveBeenCalledWith("/galaxyai/exchange-123");
        const texts = messageTexts(wrapper);
        expect(texts).toHaveLength(1);
        expect(texts[0]).toContain("New conversation started");
    });
});
