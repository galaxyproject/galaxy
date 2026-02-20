import type { components } from "@/api";
import type { PyodideTask } from "@/composables/usePyodideRunner";

// TODO: Just use schema type when metadata is no longer { [key: string]: unknown; }
export type AgentResponse = Omit<components["schemas"]["AgentResponse"], "metadata"> & {
    metadata?: {
        analysis_steps?: AnalysisStep[];
        artifacts?: UploadedArtifact[];
        datasets_used?: string[];
        executed_task?: {
            code?: string;
            task_id: string;
        };
        execution?: {
            artifacts: UploadedArtifact[];
            success: boolean;
            stdout: string;
            stderr: string;
            task_id: string;
        };
        error?: string;
        files?: string[];
        handoff_info?: {
            source_agent: string;
        };
        model?: string;
        plots?: string[];
        pyodide_status?: "completed" | "error" | "pending" | "timeout";
        pyodide_task?: PyodideTask;
        pyodide_timeout_reason?: string;
        pyodide_timeout_seconds?: number;
        pyodide_retry_count?: number;
        is_complete?: boolean;
        stdout?: string;
        stderr?: string;
        summary?: string;
        tool_yaml?: string;
        total_tokens?: number;
    };
};
export type ActionSuggestion = components["schemas"]["ActionSuggestion"];
export type ActionType = components["schemas"]["ActionType"];
export type ConfidenceLevel = components["schemas"]["ConfidenceLevel"];

export interface AnalysisStep {
    type: "thought" | "action" | "observation" | "conclusion";
    content: string;
    requirements?: string[];
    status?: "pending" | "running" | "completed" | "error";
    stdout?: string;
    stderr?: string;
    success?: boolean;
}

export interface Message {
    id: string;
    role: "user" | "assistant";
    content: string;
    timestamp: Date;
    agentType?: string;
    confidence?: ConfidenceLevel;
    feedback?: "up" | "down" | null;
    agentResponse?: AgentResponse | null;
    suggestions?: ActionSuggestion[];
    isSystemMessage?: boolean; // Flag for welcome/placeholder messages that shouldn't have feedback
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
    collapsedHistory?: Message[];
}

export interface ChatHistoryItem {
    id: number;
    query: string;
    response: string;
    agent_type: string;
    agent_response?: AgentResponse;
    timestamp: string;
    feedback?: number | null;
}

export interface UploadedArtifact {
    dataset_id: string;
    name?: string;
    size?: number;
    mime_type?: string;
    download_url: string;
    history_id?: string;
}

export interface ExecutionState {
    status: "pending" | "initialising" | "installing" | "fetching" | "running" | "submitting" | "completed" | "error";
    stdout: string;
    stderr: string;
    artifacts: UploadedArtifact[];
    errorMessage?: string;
}
