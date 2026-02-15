import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import type { ActionSuggestion, ChatMessage } from "@/composables/agentActions";
import { ActionType } from "@/composables/agentActions";

import ChatMessageCell from "./ChatMessageCell.vue";

function makeUserMessage(overrides: Partial<ChatMessage> = {}): ChatMessage {
    return {
        id: "msg-1",
        role: "user",
        content: "What tools can analyze my data?",
        timestamp: new Date(),
        feedback: null,
        ...overrides,
    };
}

function makeAssistantMessage(overrides: Partial<ChatMessage> = {}): ChatMessage {
    return {
        id: "msg-2",
        role: "assistant",
        content: "You can use the **Dataset Analyzer** tool.",
        timestamp: new Date(),
        agentType: "auto",
        feedback: null,
        ...overrides,
    };
}

const defaultRenderMarkdown = (text: string) => `<p>${text}</p>`;

function mountCell(message: ChatMessage, props: Record<string, unknown> = {}) {
    return mount(ChatMessageCell as any, {
        propsData: {
            message,
            renderMarkdown: defaultRenderMarkdown,
            processingAction: false,
            ...props,
        },
        stubs: {
            FontAwesomeIcon: true,
            ActionCard: true,
        },
    });
}

describe("ChatMessageCell", () => {
    describe("user messages", () => {
        it("renders query cell with user content", () => {
            const wrapper = mountCell(makeUserMessage());
            expect(wrapper.find(".notebook-cell").classes()).toContain("query-cell");
            expect(wrapper.find(".cell-content").text()).toBe("What tools can analyze my data?");
        });

        it("shows 'Query' label", () => {
            const wrapper = mountCell(makeUserMessage());
            expect(wrapper.find(".cell-label").text()).toContain("Query");
        });

        it("does not render feedback buttons", () => {
            const wrapper = mountCell(makeUserMessage());
            expect(wrapper.find(".cell-footer").exists()).toBe(false);
        });
    });

    describe("assistant messages", () => {
        it("renders response cell", () => {
            const wrapper = mountCell(makeAssistantMessage());
            expect(wrapper.find(".notebook-cell").classes()).toContain("response-cell");
        });

        it("renders markdown via renderMarkdown prop", () => {
            const wrapper = mountCell(makeAssistantMessage());
            expect(wrapper.find(".cell-content").html()).toContain("<p>You can use the **Dataset Analyzer** tool.</p>");
        });

        it("shows agent label from agentType", () => {
            const wrapper = mountCell(makeAssistantMessage({ agentType: "error_analysis" }));
            expect(wrapper.find(".cell-label").text()).toContain("Error Analysis");
        });

        it("shows default label for unknown agentType", () => {
            const wrapper = mountCell(makeAssistantMessage({ agentType: undefined }));
            expect(wrapper.find(".cell-label").text()).toContain("AI Assistant");
        });
    });

    describe("routing badge", () => {
        it("shows routing badge when handoff_info present", () => {
            const message = makeAssistantMessage({
                agentResponse: {
                    content: "test",
                    agent_type: "auto",
                    confidence: "high",
                    suggestions: [],
                    metadata: { handoff_info: { source_agent: "router" } },
                },
            });
            const wrapper = mountCell(message);
            expect(wrapper.find(".routing-badge").exists()).toBe(true);
            expect(wrapper.find(".routing-badge").text()).toContain("via Router");
        });

        it("hides routing badge when no handoff_info", () => {
            const wrapper = mountCell(makeAssistantMessage());
            expect(wrapper.find(".routing-badge").exists()).toBe(false);
        });
    });

    describe("feedback", () => {
        it("renders feedback buttons for normal assistant messages", () => {
            const wrapper = mountCell(makeAssistantMessage());
            const buttons = wrapper.findAll(".feedback-btn");
            expect(buttons.length).toBe(2);
        });

        it("emits feedback event on thumbs-up click", async () => {
            const wrapper = mountCell(makeAssistantMessage());
            const upBtn = wrapper.findAll(".feedback-btn").at(0);
            await upBtn!.trigger("click");
            expect(wrapper.emitted("feedback")).toEqual([["msg-2", "up"]]);
        });

        it("emits feedback event on thumbs-down click", async () => {
            const wrapper = mountCell(makeAssistantMessage());
            const downBtn = wrapper.findAll(".feedback-btn").at(1);
            await downBtn!.trigger("click");
            expect(wrapper.emitted("feedback")).toEqual([["msg-2", "down"]]);
        });

        it("disables feedback buttons after feedback given", () => {
            const wrapper = mountCell(makeAssistantMessage({ feedback: "up" }));
            const buttons = wrapper.findAll(".feedback-btn");
            expect((buttons.at(0)!.element as HTMLButtonElement).disabled).toBe(true);
            expect((buttons.at(1)!.element as HTMLButtonElement).disabled).toBe(true);
        });

        it("shows thanks text after feedback", () => {
            const wrapper = mountCell(makeAssistantMessage({ feedback: "up" }));
            expect(wrapper.find(".feedback-text").text()).toBe("Thanks!");
        });

        it("hides footer for error messages", () => {
            const wrapper = mountCell(makeAssistantMessage({ content: "❌ Something failed" }));
            expect(wrapper.find(".cell-footer").exists()).toBe(false);
        });

        it("hides footer for system messages", () => {
            const wrapper = mountCell(makeAssistantMessage({ isSystemMessage: true }));
            expect(wrapper.find(".cell-footer").exists()).toBe(false);
        });
    });

    describe("response stats", () => {
        it("shows model name when metadata.model present", () => {
            const message = makeAssistantMessage({
                agentResponse: {
                    content: "test",
                    agent_type: "auto",
                    confidence: "high",
                    suggestions: [],
                    metadata: { model: "openai/gpt-4" },
                },
            });
            const wrapper = mountCell(message);
            expect(wrapper.find(".response-stats").text()).toContain("gpt-4");
        });

        it("shows token count when metadata.total_tokens present", () => {
            const message = makeAssistantMessage({
                agentResponse: {
                    content: "test",
                    agent_type: "auto",
                    confidence: "high",
                    suggestions: [],
                    metadata: { total_tokens: 150 },
                },
            });
            const wrapper = mountCell(message);
            expect(wrapper.find(".response-stats").text()).toContain("150 tokens");
        });
    });

    describe("action suggestions", () => {
        it("renders ActionCard when suggestions present", () => {
            const suggestions: ActionSuggestion[] = [
                {
                    action_type: ActionType.TOOL_RUN,
                    description: "Run the tool",
                    parameters: {},
                    confidence: "high",
                    priority: 1,
                },
            ];
            const wrapper = mountCell(makeAssistantMessage({ suggestions }));
            expect(wrapper.find(".action-card").exists()).toBe(true);
        });

        it("does not render ActionCard when no suggestions", () => {
            const wrapper = mountCell(makeAssistantMessage());
            expect(wrapper.find(".action-card").exists()).toBe(false);
        });
    });

    describe("slots", () => {
        it("renders after-content slot", () => {
            const wrapper = mount(ChatMessageCell as any, {
                propsData: {
                    message: makeAssistantMessage(),
                    renderMarkdown: defaultRenderMarkdown,
                    processingAction: false,
                },
                stubs: {
                    FontAwesomeIcon: true,
                    ActionCard: true,
                },
                slots: {
                    "after-content": "<div class='custom-slot'>Extra content</div>",
                },
            });
            expect(wrapper.find(".custom-slot").exists()).toBe(true);
            expect(wrapper.find(".custom-slot").text()).toBe("Extra content");
        });
    });
});
