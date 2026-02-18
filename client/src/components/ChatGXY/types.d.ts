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
    confidence?: string;
    feedback?: "up" | "down" | null;
    agentResponse?: AgentResponse;
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
    agent_response?: AgentResponse; // Full agent response with suggestions
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
