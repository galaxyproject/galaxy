import type { IconDefinition } from "@fortawesome/fontawesome-svg-core";
import {
    faBug,
    faChartBar,
    faGraduationCap,
    faMagic,
    faPlus,
    faRobot,
    faRoute,
} from "@fortawesome/free-solid-svg-icons";

import type { AgentResponse } from "@/composables/agentActions";

export interface AgentType {
    value: string;
    label: string;
    icon: IconDefinition;
    description: string;
}

export const agentTypes: AgentType[] = [
    { value: "auto", label: "Auto (Router)", icon: faMagic, description: "Intelligent routing" },
    { value: "router", label: "Router", icon: faRoute, description: "Query router" },
    { value: "error_analysis", label: "Error Analysis", icon: faBug, description: "Debug tool errors" },
    { value: "custom_tool", label: "Custom Tool", icon: faPlus, description: "Create custom tools" },
    { value: "dataset_analyzer", label: "Dataset Analyzer", icon: faChartBar, description: "Analyze datasets" },
    { value: "gtn_training", label: "GTN Training", icon: faGraduationCap, description: "Find tutorials" },
];

export const agentIconMap: Record<string, IconDefinition> = {
    auto: faMagic,
    router: faRoute,
    error_analysis: faBug,
    custom_tool: faPlus,
    dataset_analyzer: faChartBar,
    gtn_training: faGraduationCap,
};

export function getAgentIcon(agentType?: string): IconDefinition {
    return agentIconMap[agentType || ""] || faRobot;
}

export function getAgentLabel(agentType?: string): string {
    const agent = agentTypes.find((a) => a.value === agentType);
    return agent?.label || agentType || "AI Assistant";
}

export function formatModelName(model?: string): string {
    if (!model) {
        return "";
    }
    const parts = model.split("/");
    return parts[parts.length - 1] || model;
}

export function getAgentResponseOrEmpty(response?: AgentResponse): AgentResponse {
    return (
        response || ({ content: "", agent_type: "", confidence: "low", suggestions: [], metadata: {} } as AgentResponse)
    );
}
