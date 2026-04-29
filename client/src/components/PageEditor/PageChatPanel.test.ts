import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import type { Pinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { usePageEditorStore } from "@/stores/pageEditorStore";

import PageChatPanel from "./PageChatPanel.vue";
import ChatInput from "@/components/ChatGXY/ChatInput.vue";
import ChatMessageCell from "@/components/ChatGXY/ChatMessageCell.vue";

// Mock GalaxyApi
const mockPOST = vi.fn();
const mockGET = vi.fn();
const mockPUT = vi.fn();

vi.mock("@/api", () => ({
    GalaxyApi: () => ({
        POST: mockPOST,
        GET: mockGET,
        PUT: mockPUT,
    }),
}));

vi.mock("vue-router/composables", () => ({
    useRouter: vi.fn(() => ({ push: vi.fn() })),
    useRoute: vi.fn(() => ({ params: {} })),
}));

const localVue = getLocalVue();

const HISTORY_ID = "history-1";
const PAGE_ID = "page-1";
const PAGE_CONTENT = "# Intro\nSome intro text\n# Methods\nSome methods text";

let pinia: Pinia;

function mountComponent(
    propsData: { historyId?: string; pageId: string; pageContent: string } = {
        historyId: HISTORY_ID,
        pageId: PAGE_ID,
        pageContent: PAGE_CONTENT,
    },
) {
    return mount(PageChatPanel as any, {
        localVue,
        propsData,
        pinia,
        stubs: {
            FontAwesomeIcon: true,
            BSkeleton: true,
            LoadingSpan: true,
            ChatMessageCell: true,
            ProposalDiffView: true,
            SectionPatchView: true,
        },
    });
}

describe("PageChatPanel", () => {
    beforeEach(() => {
        pinia = createTestingPinia({ createSpy: vi.fn });
        vi.clearAllMocks();
        // Default: no page chat history
        mockGET.mockResolvedValue({ data: [], error: null });
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    describe("Initial render", () => {
        it("renders chat panel container", async () => {
            const wrapper = mountComponent();
            await flushPromises();
            expect(wrapper.find('[data-description="page chat panel"]').exists()).toBe(true);
        });

        it("renders header with Markdown Assistant title", async () => {
            const wrapper = mountComponent();
            await flushPromises();
            expect(wrapper.find(".chat-panel-header").text()).toContain("Markdown Assistant");
        });

        it("renders ChatInput component", async () => {
            const wrapper = mountComponent();
            await flushPromises();
            expect(wrapper.findComponent(ChatInput).exists()).toBe(true);
        });

        it("shows welcome message when no history", async () => {
            const wrapper = mountComponent();
            await flushPromises();
            const cells = wrapper.findAllComponents(ChatMessageCell);
            expect(cells.length).toBe(1);
        });

        it("renders new conversation button", async () => {
            const wrapper = mountComponent();
            await flushPromises();
            expect(wrapper.find('[data-description="new conversation button"]').exists()).toBe(true);
        });
    });

    describe("Message submission", () => {
        it("sends query to API on submit", async () => {
            mockPOST.mockResolvedValue({
                data: {
                    response: "I can help with that.",
                    exchange_id: 42,
                    agent_response: {
                        agent_type: "page_assistant",
                        confidence: "high",
                        suggestions: [],
                        metadata: {},
                    },
                },
                error: null,
            });

            const wrapper = mountComponent();
            await flushPromises();

            // Use ChatInput's v-model: set value via the textarea + trigger submit
            const textarea = wrapper.find("textarea");
            await textarea.setValue("Rewrite the intro section");
            await wrapper.find(".send-button").trigger("click");
            await flushPromises();

            expect(mockPOST).toHaveBeenCalledWith(
                "/api/chat",
                expect.objectContaining({
                    params: { query: { agent_type: "page_assistant" } },
                }),
            );
        });

        it("adds user and assistant messages after submit", async () => {
            mockPOST.mockResolvedValue({
                data: {
                    response: "Here is a rewrite.",
                    exchange_id: 42,
                    agent_response: {
                        agent_type: "page_assistant",
                        confidence: "high",
                        suggestions: [],
                        metadata: {},
                    },
                },
                error: null,
            });

            const wrapper = mountComponent();
            await flushPromises();

            const textarea = wrapper.find("textarea");
            await textarea.setValue("Rewrite intro");
            await wrapper.find(".send-button").trigger("click");
            await flushPromises();

            const cells = wrapper.findAllComponents(ChatMessageCell);
            // Welcome + user + assistant = 3
            expect(cells.length).toBe(3);
        });

        it("shows error message on API failure", async () => {
            mockPOST.mockResolvedValue({
                data: null,
                error: { err_msg: "Server error" },
            });

            const wrapper = mountComponent();
            await flushPromises();

            const textarea = wrapper.find("textarea");
            await textarea.setValue("test query");
            await wrapper.find(".send-button").trigger("click");
            await flushPromises();

            const cells = wrapper.findAllComponents(ChatMessageCell);
            const lastCell = cells.at(cells.length - 1);
            expect(lastCell.props("message").content).toContain("Error");
        });

        it("sets exchange_id from response for follow-up queries", async () => {
            mockPOST.mockResolvedValue({
                data: { response: "Done.", exchange_id: 99, agent_response: null },
                error: null,
            });

            const wrapper = mountComponent();
            await flushPromises();

            const textarea = wrapper.find("textarea");
            await textarea.setValue("hello");
            await wrapper.find(".send-button").trigger("click");
            await flushPromises();

            // Subsequent request should include the exchange_id
            mockPOST.mockResolvedValue({
                data: { response: "Follow up.", exchange_id: 99, agent_response: null },
                error: null,
            });

            await textarea.setValue("follow up");
            await wrapper.find(".send-button").trigger("click");
            await flushPromises();

            const lastCall = mockPOST.mock.calls[mockPOST.mock.calls.length - 1]!;
            expect(lastCall[1].body.exchange_id).toBe(99);
        });
    });

    describe("New conversation", () => {
        it("resets messages on new conversation click", async () => {
            mockPOST.mockResolvedValue({
                data: { response: "Test", exchange_id: 1, agent_response: null },
                error: null,
            });

            const wrapper = mountComponent();
            await flushPromises();

            const textarea = wrapper.find("textarea");
            await textarea.setValue("hello");
            await wrapper.find(".send-button").trigger("click");
            await flushPromises();

            // Click new conversation
            await wrapper.find('[data-description="new conversation button"]').trigger("click");
            await flushPromises();

            const cells = wrapper.findAllComponents(ChatMessageCell);
            expect(cells.length).toBe(1);
        });
    });

    describe("Loading state", () => {
        it("shows loading indicator when busy", async () => {
            // Make POST never resolve to keep busy=true
            mockPOST.mockReturnValue(new Promise(() => {}));

            const wrapper = mountComponent();
            await flushPromises();

            const textarea = wrapper.find("textarea");
            await textarea.setValue("hello");
            await wrapper.find(".send-button").trigger("click");
            await wrapper.vm.$nextTick();

            expect(wrapper.find('[data-description="chat loading indicator"]').exists()).toBe(true);
        });
    });

    describe("Store integration", () => {
        it("does not call store methods on mount", async () => {
            const store = usePageEditorStore();
            mountComponent();
            await flushPromises();

            expect(store.updateContent).not.toHaveBeenCalled();
            expect(store.savePage).not.toHaveBeenCalled();
        });
    });

    describe("Chat persistence", () => {
        it("stores exchange ID in store after first submit", async () => {
            mockPOST.mockResolvedValue({
                data: { response: "Done.", exchange_id: 77, agent_response: null },
                error: null,
            });
            const wrapper = mountComponent();
            await flushPromises();
            const store = usePageEditorStore();

            const textarea = wrapper.find("textarea");
            await textarea.setValue("hello");
            await wrapper.find(".send-button").trigger("click");
            await flushPromises();

            expect(store.setCurrentChatExchangeId).toHaveBeenCalledWith(PAGE_ID, 77);
        });

        it("clears stored exchange ID on new conversation", async () => {
            const wrapper = mountComponent();
            await flushPromises();
            const store = usePageEditorStore();

            await wrapper.find('[data-description="new conversation button"]').trigger("click");
            await flushPromises();

            expect(store.setCurrentChatExchangeId).toHaveBeenCalledWith(PAGE_ID, null);
        });

        it("checks store for cached exchange ID on mount", async () => {
            const store = usePageEditorStore();
            vi.mocked(store.getCurrentChatExchangeId).mockReturnValue("abc55");
            // Mock the exchange messages load
            mockGET.mockResolvedValue({
                data: [
                    { role: "user", content: "hello", timestamp: null },
                    { role: "assistant", content: "hi", agent_type: "page_assistant", timestamp: null },
                ],
                error: null,
            });

            const wrapper = mountComponent();
            await flushPromises();

            expect(store.getCurrentChatExchangeId).toHaveBeenCalledWith(PAGE_ID);
            // Should have loaded 2 messages from the cached conversation
            const cells = wrapper.findAllComponents(ChatMessageCell);
            expect(cells.length).toBe(2);
        });

        it("falls back to API when stored exchange ID returns empty messages", async () => {
            const store = usePageEditorStore();
            vi.mocked(store.getCurrentChatExchangeId).mockReturnValue("abc999");
            // All GET calls return empty — stored exchange has no messages, no page history
            mockGET.mockResolvedValue({ data: [], error: null });

            const wrapper = mountComponent();
            await flushPromises();

            // Stored ID yielded nothing, API fallback yielded nothing — welcome message shown
            const cells = wrapper.findAllComponents(ChatMessageCell);
            expect(cells.length).toBe(1);
        });
    });

    describe("Standalone page mode (no historyId)", () => {
        function mountStandalone() {
            return mountComponent({ pageId: PAGE_ID, pageContent: PAGE_CONTENT });
        }

        it("renders header with Markdown Assistant title", async () => {
            const wrapper = mountStandalone();
            await flushPromises();
            expect(wrapper.find(".chat-panel-header").text()).toContain("Markdown Assistant");
        });

        it("shows Markdown Assistant welcome message", async () => {
            const wrapper = mountStandalone();
            await flushPromises();
            const cells = wrapper.findAllComponents(ChatMessageCell);
            expect(cells.length).toBe(1);
            // The welcome message should mention "Markdown Assistant"
            expect(cells.at(0).props("message").content).toContain("Markdown Assistant");
        });

        it("sends query to API without historyId", async () => {
            mockPOST.mockResolvedValue({
                data: {
                    response: "I can help with that.",
                    exchange_id: 42,
                    agent_response: null,
                },
                error: null,
            });

            const wrapper = mountStandalone();
            await flushPromises();

            const textarea = wrapper.find("textarea");
            await textarea.setValue("Rewrite the intro");
            await wrapper.find(".send-button").trigger("click");
            await flushPromises();

            expect(mockPOST).toHaveBeenCalledWith(
                "/api/chat",
                expect.objectContaining({
                    params: { query: { agent_type: "page_assistant" } },
                }),
            );
        });

        it("renders Markdown Assistant header when historyId is provided", async () => {
            const wrapper = mountComponent();
            await flushPromises();
            expect(wrapper.find(".chat-panel-header").text()).toContain("Markdown Assistant");
        });
    });
});
