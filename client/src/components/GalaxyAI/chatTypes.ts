import type { components } from "@/api";
import type { ActionSuggestion, AgentResponse } from "@/composables/agentActions";

export type ChatHistoryItem = components["schemas"]["ChatHistoryItemResponse"];

export interface ChatMessage {
    id: string;
    role: "user" | "assistant";
    content: string;
    timestamp: Date;
    agentType?: string;
    confidence?: string;
    feedback?: "up" | "down" | null;
    agentResponse?: AgentResponse;
    suggestions?: ActionSuggestion[];
    isSystemMessage?: boolean;
}
