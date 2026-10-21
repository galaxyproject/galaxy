import type { ChatHistoryItem } from "@/components/GalaxyAI/chatTypes";

export function getFakeChatHistoryItem(overrides: Partial<ChatHistoryItem> = {}): ChatHistoryItem {
    return {
        id: "chat-1",
        query: "Test question",
        response: "Test answer",
        agent_type: "galaxy",
        timestamp: "2026-01-01T00:00:00",
        ...overrides,
    };
}
