/**
 * Composable for handling AI agent action suggestions in the UI
 */

import { ref } from "vue";
import { useRouter } from "vue-router/composables";
import { parse } from "yaml";

import { type DynamicUnprivilegedToolCreatePayload, GalaxyApi } from "@/api";
import { useConfig } from "@/composables/config";
import { useToast } from "@/composables/toast";
import { useUnprivilegedToolStore } from "@/stores/unprivilegedToolStore";

/* eslint-disable no-unused-vars */
// Action types from backend - values are used in switch/case and icon maps
export enum ActionType {
    TOOL_RUN = "tool_run",
    DOCUMENTATION = "documentation",
    CONTACT_SUPPORT = "contact_support",
    VIEW_EXTERNAL = "view_external",
    SAVE_TOOL = "save_tool",
    REFINE_QUERY = "refine_query",
    PYODIDE_EXECUTE = "pyodide_execute",
}
/* eslint-enable no-unused-vars */

export interface ActionSuggestion {
    action_type: ActionType;
    description: string;
    parameters: Record<string, any>;
    confidence: "low" | "medium" | "high";
    priority: number;
}

export interface AgentResponse {
    content: string;
    agent_type: string;
    confidence: "low" | "medium" | "high";
    suggestions: ActionSuggestion[];
    metadata: Record<string, any>;
    reasoning?: string;
}

export function useAgentActions() {
    const router = useRouter();
    const toast = useToast();
    const { config } = useConfig();
    const unprivilegedToolStore = useUnprivilegedToolStore();
    const processingAction = ref(false);

    /**
     * Handle an action suggestion from an agent response
     */
    async function handleAction(action: ActionSuggestion, agentResponse: AgentResponse) {
        processingAction.value = true;

        try {
            switch (action.action_type) {
                case ActionType.TOOL_RUN:
                    await handleToolRun(action);
                    break;

                case ActionType.SAVE_TOOL:
                    await handleSaveTool(agentResponse);
                    break;

                case ActionType.CONTACT_SUPPORT:
                    handleContactSupport();
                    break;

                case ActionType.REFINE_QUERY:
                    toast.info("Please refine your query with more details");
                    break;

                case ActionType.VIEW_EXTERNAL:
                    handleViewExternal(action);
                    break;

                case ActionType.DOCUMENTATION:
                    handleDocumentation(action);
                    break;

                case ActionType.PYODIDE_EXECUTE:
                    toast.info("Generated code is running automatically in the browser.");
                    break;

                default:
                    // Unknown actions default to contact support
                    console.warn(`Unknown action type: ${action.action_type}, redirecting to support`);
                    handleContactSupport();
            }
        } catch (error) {
            console.error("Error handling action:", error);
            const errorMessage = error instanceof Error ? error.message : String(error);
            toast.error(`Failed to perform action: ${errorMessage}`);
        } finally {
            processingAction.value = false;
        }
    }

    /**
     * Handle TOOL_RUN action - navigate to tool with parameters
     */
    async function handleToolRun(action: ActionSuggestion) {
        const toolId = action.parameters.tool_id;
        const params = action.parameters.tool_params || {};

        if (!toolId) {
            toast.error("No tool ID provided for tool run action");
            return;
        }

        // Navigate to tool panel with the tool ID
        router.push({
            path: "/",
            query: {
                tool_id: toolId,
                ...params,
            },
        });

        toast.success(`Opening tool: ${toolId}`);
    }

    /**
     * Handle SAVE_TOOL action - save custom tool as unprivileged user tool
     */
    async function handleSaveTool(agentResponse: AgentResponse) {
        const toolYaml = agentResponse.metadata?.tool_yaml;

        if (!toolYaml) {
            toast.error("No tool YAML provided for save action");
            return;
        }

        try {
            const representation = parse(toolYaml);
            const payload: DynamicUnprivilegedToolCreatePayload = {
                active: true,
                hidden: false,
                representation,
                src: "representation",
            };

            const { data, error } = await GalaxyApi().POST("/api/unprivileged_tools", { body: payload });

            if (error) {
                toast.error(`Failed to save tool: ${String(error)}`);
                return;
            }

            toast.success(`Tool "${data.representation.name}" saved successfully!`);
            unprivilegedToolStore.load(true);
            router.push(`/tools/editor/${data.uuid}`);
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : String(err);
            toast.error(`Error saving tool: ${errorMessage}`);
        }
    }

    /**
     * Handle CONTACT_SUPPORT action - use configured support URL or default
     */
    function handleContactSupport() {
        const supportUrl = config.value.support_url || "https://galaxyproject.org/support/";
        window.open(supportUrl, "_blank");
        toast.info("Opening Galaxy support page");
    }

    /**
     * Handle VIEW_EXTERNAL action - open external URL in new tab
     */
    function handleViewExternal(action: ActionSuggestion) {
        const url = action.parameters.url;

        if (!url) {
            toast.error("No URL provided for external view action");
            return;
        }

        // Open URL in new tab
        window.open(url, "_blank");
        toast.success("Opening in new tab");
    }

    /**
     * Handle DOCUMENTATION action - open tool documentation
     */
    function handleDocumentation(action: ActionSuggestion) {
        const toolId = action.parameters.tool_id;

        if (toolId && toolId !== "unknown") {
            // Navigate to tool help page
            router.push({
                path: "/",
                query: {
                    tool_id: toolId,
                    show_help: "true",
                },
            });
            toast.info(`Opening documentation for ${toolId}`);
        } else {
            // Open general Galaxy documentation
            window.open("https://training.galaxyproject.org/", "_blank");
            toast.info("Opening Galaxy Training Network");
        }
    }

    /**
     * Get action icon based on type
     */
    function getActionIcon(actionType: ActionType): string {
        const icons: Record<ActionType, string> = {
            [ActionType.TOOL_RUN]: "🔧",
            [ActionType.SAVE_TOOL]: "💾",
            [ActionType.DOCUMENTATION]: "📖",
            [ActionType.CONTACT_SUPPORT]: "🆘",
            [ActionType.REFINE_QUERY]: "✏️",
            [ActionType.VIEW_EXTERNAL]: "🔗",
            [ActionType.PYODIDE_EXECUTE]: "🧪",
        };
        return icons[actionType] || "❓";
    }

    /**
     * Get action button variant based on priority
     */
    function getActionVariant(priority: number): string {
        switch (priority) {
            case 1:
                return "primary";
            case 2:
                return "secondary";
            case 3:
                return "info";
            default:
                return "light";
        }
    }

    return {
        processingAction,
        handleAction,
        getActionIcon,
        getActionVariant,
    };
}
