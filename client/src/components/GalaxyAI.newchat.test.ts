import { getLocalVue } from "@tests/vitest/helpers";
import { mount, type Wrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import { useChatStore } from "@/stores/chatStore";

import GalaxyAI from "./GalaxyAI.vue";

const { mockGet, mockPost, mockPut, ChatMessageCellStub, ChatInputStub } = vi.hoisted(() => ({
    mockGet: vi.fn(),
    mockPost: vi.fn(),
    mockPut: vi.fn(),
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

vi.mock("vue-router/composables", () => ({
    useRoute: () => ({ path: "/", params: {}, query: {} }),
    useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
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

describe("GalaxyAI", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockGet.mockResolvedValue({ data: [], error: undefined });
    });

    it("appends the response and records the exchange id on a normal exchange", async () => {
        mockPost.mockResolvedValue({
            data: { response: "Here you go", exchange_id: "exchange-123" },
            error: undefined,
        });
        const { wrapper, chatStore } = mountChat();
        await flushPromises();

        await sendMessage(wrapper, "find me a mapper");

        const texts = messageTexts(wrapper);
        expect(texts).toHaveLength(3);
        expect(texts[1]).toBe("find me a mapper");
        expect(texts[2]).toBe("Here you go");
        expect(chatStore.activeChatId).toBe("exchange-123");
    });

    it("resets an unsaved conversation when a new chat is requested mid-flight", async () => {
        const deferred = deferredResponse();
        mockPost.mockReturnValue(deferred.promise);
        const { wrapper, chatStore } = mountChat();
        await flushPromises();

        await sendMessage(wrapper, "what mappers are available?");
        expect(messageTexts(wrapper)).toHaveLength(2);
        expect(wrapper.find(".loading-entry").exists()).toBe(true);
        // the conversation is unsaved — no exchange id yet, so the identity
        // (activeChatId) would not change and a plain showChat(null) is a no-op
        expect(chatStore.activeChatId).toBeNull();

        chatStore.requestNewChat();
        await flushPromises();

        const texts = messageTexts(wrapper);
        expect(texts).toHaveLength(1);
        expect(texts[0]).toContain("New conversation started");
        expect(wrapper.find(".loading-entry").exists()).toBe(false);

        // the stale response must not be appended or re-attach the old exchange
        deferred.resolve({ data: { response: "Late answer", exchange_id: "exchange-123" }, error: undefined });
        await flushPromises();

        expect(messageTexts(wrapper)).toHaveLength(1);
        expect(chatStore.activeChatId).toBeNull();
    });

    it("does not let a stale response clobber a newly started conversation", async () => {
        const first = deferredResponse();
        const second = deferredResponse();
        mockPost.mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise);
        const { wrapper, chatStore } = mountChat();
        await flushPromises();

        await sendMessage(wrapper, "first question");
        chatStore.requestNewChat();
        await flushPromises();
        await sendMessage(wrapper, "second question");
        expect(wrapper.find(".loading-entry").exists()).toBe(true);

        first.resolve({ data: { response: "First answer", exchange_id: "exchange-1" }, error: undefined });
        await flushPromises();

        // still only welcome + second user message, still waiting on the second response
        let texts = messageTexts(wrapper);
        expect(texts).toHaveLength(2);
        expect(texts[1]).toBe("second question");
        expect(wrapper.find(".loading-entry").exists()).toBe(true);
        expect(chatStore.activeChatId).toBeNull();

        second.resolve({ data: { response: "Second answer", exchange_id: "exchange-2" }, error: undefined });
        await flushPromises();

        texts = messageTexts(wrapper);
        expect(texts).toHaveLength(3);
        expect(texts[2]).toBe("Second answer");
        expect(wrapper.find(".loading-entry").exists()).toBe(false);
        expect(chatStore.activeChatId).toBe("exchange-2");
    });
});
