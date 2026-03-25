import type { components } from "@/api";

export type AgentResponse = components["schemas"]["AgentResponse"];
export type ActionSuggestion = components["schemas"]["ActionSuggestion"];
export type ActionType = components["schemas"]["ActionType"];
export type AnalysisStep = components["schemas"]["AnalysisStep"];
export type ConfidenceLevel = components["schemas"]["ConfidenceLevel"];
export type UploadedArtifact = components["schemas"]["UploadedArtifact"];

export interface ChatMessage {
    id: string;
    role: "user" | "assistant";
    content: string;
    timestamp: Date;
    agentType?: string;
    confidence?: ConfidenceLevel;
    feedback?: "up" | "down" | null;
    agentResponse?: AgentResponse | null;
    suggestions?: ActionSuggestion[];
    isSystemMessage?: boolean;
    routingInfo?: {
        selected_agent: string;
        reasoning: string;
    };
    analysisSteps?: AnalysisStep[];
    artifacts?: UploadedArtifact[];
    generatedPlots?: string[];
    generatedFiles?: string[];
    isCollapsible?: boolean;
    isCollapsed?: boolean;
    collapsedHistory?: ChatMessage[];
}

export interface ChatHistoryItem {
    id: string;
    query: string;
    response: string;
    agent_type: string;
    agent_response?: AgentResponse;
    timestamp: string;
    feedback?: number | null;
}

export interface ExchangeMessage {
    role: string;
    content?: string | null;
    timestamp?: string | null;
    task_id?: string | null;
    agent_type?: string | null;
    agent_response?: components["schemas"]["AgentResponse"] | null;
    feedback?: number | null;
    dataset_ids?: string[] | null;
    stdout?: string;
    stderr?: string;
    artifacts?: unknown[];
    success?: boolean;
    metadata?: Record<string, unknown>;
}

export interface ExecutionState {
    status: "pending" | "initialising" | "installing" | "fetching" | "running" | "submitting" | "completed" | "error";
    stdout: string;
    stderr: string;
    artifacts: UploadedArtifact[];
    errorMessage?: string;
}
