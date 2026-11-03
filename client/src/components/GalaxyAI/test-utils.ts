import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { mount, type VueWrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia, setActivePinia } from "pinia";
import { vi } from "vitest";
import { h, nextTick, ref } from "vue";

import { useChatStore } from "@/stores/chatStore";

import GalaxyAI from "../GalaxyAI.vue";

const api = vi.hoisted(() => ({ GET: vi.fn(), POST: vi.fn(), PUT: vi.fn(), DELETE: vi.fn() }));

const stubs = vi.hoisted(() => ({
    // render functions because the test environment uses the runtime-only Vue build
    ChatMessageCellStub: {
        name: "ChatMessageCellStub",
        props: ["message"],
        render(this: { message: { content: string } }) {
            return h("div", { class: "chat-message-stub" }, [this.message.content]);
        },
    },
    ChatInputStub: {
        name: "ChatInputStub",
        props: ["value", "busy"],
        render() {
            return h("input", { class: "chat-input-stub" });
        },
    },
}));

vi.mock("@/api", () => ({ GalaxyApi: () => api }));
vi.mock("@/api/client", () => ({ GalaxyApi: () => api }));

// Child components are referenced directly from setup scope, so the test-utils
// `stubs` option cannot replace them — mock the modules instead.
vi.mock("@/components/GalaxyAI/ChatMessageCell.vue", () => ({ default: stubs.ChatMessageCellStub }));
vi.mock("@/components/GalaxyAI/ChatInput.vue", () => ({ default: stubs.ChatInputStub }));

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

vi.mock("@/composables/toast");

vi.mock("@/composables/useEntityMentions", () => ({
    MENTION_PATTERN_SOURCE: "@(dataset|history):(\\S+)",
    parseMentions: () => [],
    resolveMentions: () => [],
    buildEntityContext: () => null,
}));

vi.mock("@/composables/userLocalStorage", () => ({
    useUserLocalStorage: vi.fn((_key: string, initialValue: unknown) => ref(initialValue)),
}));

/** The `GalaxyApi().GET` and `.POST` spies behind every request the chat makes. */
export const mockGet = api.GET;
export const mockPost = api.POST;

export const { ChatInputStub } = stubs;

const localVue = getLocalVue();

/**
 * Mount GalaxyAI (as a panel unless `props` say otherwise) with its message
 * cells and input stubbed and a real chat store, once its initial loads settle.
 * Import GalaxyAI through this helper only, so the mocks above apply to it.
 */
export async function mountChat(props: Record<string, unknown> = {}) {
    const pinia = createPinia();
    setActivePinia(pinia);
    const wrapper = mount(GalaxyAI, {
        props: { panel: true, ...props },
        global: {
            ...withPlugins(localVue, pinia),
            stubs: { ...localVue.stubs, FontAwesomeIcon: true, BSkeleton: true },
        },
    });
    await flushPromises();
    return { wrapper, chatStore: useChatStore() };
}

/** The text of every message in the conversation, oldest first. */
export function messageTexts(wrapper: VueWrapper) {
    return wrapper.findAll(".chat-message-stub").map((message) => message.text());
}

/** Type `text` into the chat input, submit it, and let the request start. */
export async function sendMessage(wrapper: VueWrapper, text: string) {
    const input = wrapper.findComponent(ChatInputStub);
    input.vm.$emit("input", text);
    await nextTick();
    input.vm.$emit("submit");
    await flushPromises();
}

/** A successful `POST /api/chat` result. */
export function chatReply(response: string, exchangeId: string) {
    return { data: { response, exchange_id: exchangeId }, error: undefined };
}
