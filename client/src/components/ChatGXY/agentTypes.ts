import type { IconDefinition } from "@fortawesome/fontawesome-svg-core";
import {
    faBook,
    faBug,
    faChartBar,
    faGraduationCap,
    faMagic,
    faPlus,
    faRobot,
    faRoute,
} from "@fortawesome/free-solid-svg-icons";

import { AGENT_LABELS } from "@/components/Page/constants";
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
    {
        value: "page_assistant",
        label: AGENT_LABELS.pageAssistantLabel,
        icon: faBook,
        description: AGENT_LABELS.pageAssistantDescription,
    },
];

export function getAgentIcon(agentType?: string): IconDefinition {
    return agentTypes.find((a) => a.value === agentType)?.icon || faRobot;
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
