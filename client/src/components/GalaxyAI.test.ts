import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import { useServerMock } from "@/api/client/__mocks__";
import type { ActiveContext } from "@/composables/useActiveContext";
import { useChatStore } from "@/stores/chatStore";
import { usePageEditorStore } from "@/stores/pageEditorStore";

import GalaxyAI from "./GalaxyAI.vue";

// API mock
const { server, http } = useServerMock();

const mockGetMessages = vi.fn();
const mockGetHistory = vi.fn();

// Composable mocks
const mockActiveContext = ref<ActiveContext | null>(null);

vi.mock("@/composables/useActiveContext", () => ({
    useActiveContext: () => ({ activeContext: mockActiveContext, contextLabel: ref("") }),
}));

vi.mock("@/composables/userLocalStorage", () => ({
    useUserLocalStorage: (_key: string, initial: unknown) => ref(initial),
}));

vi.mock("@/composables/markdown", () => ({
    useMarkdown: () => ({ renderMarkdown: (s: string) => s }),
}));

vi.mock("@/composables/agentActions", () => ({
    useAgentActions: () => ({ processingAction: ref(false), handleAction: vi.fn() }),
}));

vi.mock("@/composables/confirmDialog", () => ({
    useConfirmDialog: () => ({ confirm: vi.fn() }),
}));

vi.mock("@/composables/toast", () => ({
    useToast: () => ({ error: vi.fn(), success: vi.fn() }),
}));

vi.mock("@/composables/useEntityMentions", () => ({
    parseMentions: (s: string) => s,
    resolveMentions: (s: string) => s,
    buildEntityContext: () => null,
}));

vi.mock("@/composables/usePageProposals", () => ({
    usePageProposals: () => ({
        pageContent: ref(""),
        loadForPage: vi.fn(),
        clear: vi.fn(),
        getEditProposal: vi.fn(),
        isProposalStale: vi.fn(),
        isProposalVisible: vi.fn(() => false),
        buildProposedContent: vi.fn(),
        applyFullReplacement: vi.fn(),
        applySectionPatched: vi.fn(),
        dismissProposal: vi.fn(),
    }),
}));

vi.mock("vue-router/composables", () => ({
    useRoute: () => ({ path: "/", params: {}, query: {} }),
    useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}));

const localVue = getLocalVue();
let lastWrapper: ReturnType<typeof shallowMount> | null = null;

// Constants
const EXCHANGE_ID = "exchange-abc";
const MESSAGES_RESPONSE = [
    { role: "user", content: "Hello", timestamp: null },
    { role: "assistant", content: "Hi", timestamp: null, agent_type: "router", agent_response: null, feedback: null },
];

function makeSuccessfulFetch(messages = MESSAGES_RESPONSE) {
    server.use(
        http.get("/api/chat/exchange/{exchange_id}/messages", ({ response }) => {
            mockGetMessages();
            return response(200).json(messages);
        }),
    );
}

function makeEmptyFetch() {
    server.use(
        http.get("/api/chat/exchange/{exchange_id}/messages", ({ response }) => {
            mockGetMessages();
            return response(200).json([]);
        }),
    );
}

function makeHistoryFetch(items: { id: string }[] = [{ id: "latest-chat" }]) {
    server.use(
        http.get("/api/chat/history", ({ response }) => {
            mockGetHistory();
            return response(200).json(items as any);
        }),
        http.get("/api/chat/page/{page_id}/history", ({ response }) => {
            mockGetHistory();
            return response(200).json(items as any);
        }),
    );
}

interface MountOptions {
    props?: Record<string, unknown>;
    activeChatId?: string | null;
    cachedExchangeId?: string | null;
    pageId?: string;
    chatHistoryItems?: { id: string }[];
}

function mountGalaxyAI({
    props = {},
    activeChatId = null,
    cachedExchangeId = null,
    pageId = "page-1",
    chatHistoryItems,
}: MountOptions = {}) {
    const pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
    setActivePinia(pinia);

    const chatStore = useChatStore();
    chatStore.activeChatId = activeChatId as any;

    if (chatHistoryItems !== undefined) {
        chatStore.chatHistory = chatHistoryItems as any;
        vi.spyOn(chatStore, "loadHistory").mockResolvedValue(undefined);
    }

    const pageEditorStore = usePageEditorStore();
    if (cachedExchangeId) {
        pageEditorStore.setCurrentChatExchangeId(pageId, cachedExchangeId);
    }

    const wrapper = shallowMount(GalaxyAI as object, {
        localVue,
        pinia,
        propsData: props,
        stubs: {
            FontAwesomeIcon: true,
            ChatActions: true,
            ChatInput: true,
            ChatMessageCell: true,
            ProposalDiffView: true,
            SectionPatchView: true,
            Heading: true,
            BSkeleton: true,
        },
    });

    lastWrapper = wrapper;
    return { wrapper, chatStore, pageEditorStore };
}

describe("GalaxyAI fetch operations on mount", () => {
    beforeEach(() => {
        mockActiveContext.value = null;
        mockGetMessages.mockClear();
        mockGetHistory.mockClear();
        makeHistoryFetch([]);
    });

    afterEach(() => {
        lastWrapper?.destroy();
        lastWrapper = null;
        vi.restoreAllMocks();
    });

    describe("when exchangeId prop is provided and not 'new'", () => {
        it("fetches the specified exchange on mount", async () => {
            makeSuccessfulFetch();
            mountGalaxyAI({ props: { exchangeId: EXCHANGE_ID } });
            await flushPromises();
            expect(mockGetMessages).toHaveBeenCalledOnce();
        });

        it("does not call loadLatestChat", async () => {
            makeSuccessfulFetch();
            mountGalaxyAI({ props: { exchangeId: EXCHANGE_ID }, chatHistoryItems: [{ id: EXCHANGE_ID }] });
            await flushPromises();
            expect(mockGetHistory).not.toHaveBeenCalled();
        });
    });

    describe("when exchangeId prop is 'new'", () => {
        it("starts a new chat without fetching messages", async () => {
            mountGalaxyAI({ props: { exchangeId: "new" } });
            await flushPromises();
            expect(mockGetMessages).not.toHaveBeenCalled();
        });

        it("does not restore from activeChatId even when one is set", async () => {
            mountGalaxyAI({ props: { exchangeId: "new" }, activeChatId: EXCHANGE_ID });
            await flushPromises();
            expect(mockGetMessages).not.toHaveBeenCalled();
        });
    });

    describe("docked/panel — notebook context with cached exchange ID", () => {
        it("fetches the cached exchange when activeChatId is null", async () => {
            makeSuccessfulFetch();
            mockActiveContext.value = { contextType: "notebook", pageId: "page-1", historyId: "hist-1" };
            mountGalaxyAI({ props: { docked: true }, activeChatId: null, cachedExchangeId: EXCHANGE_ID });
            await flushPromises();
            expect(mockGetMessages).toHaveBeenCalledOnce();
        });

        it("clears stale cached ID when fetch returns no messages", async () => {
            makeEmptyFetch();
            mockActiveContext.value = { contextType: "notebook", pageId: "page-1", historyId: "hist-1" };
            const { pageEditorStore } = mountGalaxyAI({
                props: { docked: true },
                activeChatId: null,
                cachedExchangeId: EXCHANGE_ID,
            });
            await flushPromises();
            expect(pageEditorStore.getCurrentChatExchangeId("page-1")).toBeNull();
        });
    });

    describe("docked/panel — notebook context, no cached ID but page has history", () => {
        it("fetches the most recent chat from page history (ignores global activeChatId)", async () => {
            makeSuccessfulFetch();
            mockActiveContext.value = { contextType: "notebook", pageId: "page-1", historyId: "hist-1" };
            mountGalaxyAI({
                props: { panel: true },
                activeChatId: "some-other-chat",
                chatHistoryItems: [{ id: EXCHANGE_ID }],
            });
            await flushPromises();
            expect(mockGetMessages).toHaveBeenCalledOnce();
        });
    });

    describe("docked/panel — notebook context, no cached ID and empty history", () => {
        it("starts a new chat without fetching", async () => {
            mockActiveContext.value = { contextType: "notebook", pageId: "page-1", historyId: "hist-1" };
            mountGalaxyAI({ props: { docked: true }, activeChatId: null });
            await flushPromises();
            expect(mockGetMessages).not.toHaveBeenCalled();
        });
    });

    describe("docked/panel — non-notebook context with activeChatId", () => {
        it("fetches the active chat exchange", async () => {
            makeSuccessfulFetch();
            mountGalaxyAI({ props: { panel: true }, activeChatId: EXCHANGE_ID });
            await flushPromises();
            expect(mockGetMessages).toHaveBeenCalledOnce();
        });
    });

    describe("docked/panel — non-notebook context, no activeChatId", () => {
        it("starts a new chat without fetching", async () => {
            mountGalaxyAI({ props: { docked: true }, activeChatId: null });
            await flushPromises();
            expect(mockGetMessages).not.toHaveBeenCalled();
        });
    });

    describe("center mode (no exchangeId, not docked/panel)", () => {
        it("calls loadLatestChat to fetch most recent history", async () => {
            mountGalaxyAI({});
            await flushPromises();
            expect(mockGetHistory).toHaveBeenCalledOnce();
        });

        it("does not fetch exchange messages when history is empty", async () => {
            mountGalaxyAI({});
            await flushPromises();
            expect(mockGetMessages).not.toHaveBeenCalled();
        });

        it("fetches the latest exchange when history has items", async () => {
            makeHistoryFetch([{ id: "latest-chat" }]);
            makeSuccessfulFetch();
            mountGalaxyAI({});
            await flushPromises();
            expect(mockGetMessages).toHaveBeenCalledOnce();
        });
    });
});
