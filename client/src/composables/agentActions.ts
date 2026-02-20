/**
 * Composable for handling AI agent action suggestions in the UI
 */

import { ref } from "vue";
import { useRouter } from "vue-router/composables";
import { parse } from "yaml";

import { type DynamicUnprivilegedToolCreatePayload, GalaxyApi } from "@/api";
import type { ActionSuggestion, ActionType, AgentResponse } from "@/components/ChatGXY/types";
import { useConfig } from "@/composables/config";
import { useToast } from "@/composables/toast";
import { useUnprivilegedToolStore } from "@/stores/unprivilegedToolStore";

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
                case "tool_run":
                    await handleToolRun(action);
                    break;

                case "save_tool":
                    await handleSaveTool(agentResponse);
                    break;

                case "contact_support":
                    handleContactSupport();
                    break;

                case "refine_query":
                    toast.info("Please refine your query with more details");
                    break;

                case "view_external":
                    handleViewExternal(action);
                    break;

                case "documentation":
                    handleDocumentation(action);
                    break;

                case "pyodide_execute":
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
        const toolId = action.parameters?.tool_id as string;
        const params = action.parameters?.tool_params || {};

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
        const toolYaml = agentResponse.metadata?.tool_yaml as string;

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
        const url = action.parameters?.url as string;

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
        const toolId = action.parameters?.tool_id as string;

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
            tool_run: "🔧",
            save_tool: "💾",
            documentation: "📖",
            contact_support: "🆘",
            refine_query: "✏️",
            view_external: "🔗",
            pyodide_execute: "🧪",
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
