/**
 * Composable for handling AI agent action suggestions in the UI
 */

import { ref } from "vue";
import { useRouter } from "vue-router/composables";

import { useToast } from "@/composables/toast";
import { getAppRoot } from "@/onload/loadConfig";

// Action types from backend
export enum ActionType {
    TOOL_RUN = "tool_run",
    PARAMETER_CHANGE = "parameter_change",
    WORKFLOW_STEP = "workflow_step",
    CONTACT_SUPPORT = "contact_support",
    SAVE_TOOL = "save_tool",
    TEST_TOOL = "test_tool",
    REFINE_QUERY = "refine_query",
    VIEW_EXTERNAL = "view_external",
}

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
    const processingAction = ref(false);
    const showToolModal = ref(false);
    const toolModalContent = ref<any>({});

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
                    await handleSaveTool(action, agentResponse);
                    break;

                case ActionType.TEST_TOOL:
                    await handleTestTool(action, agentResponse);
                    break;

                case ActionType.PARAMETER_CHANGE:
                    await handleParameterChange(action);
                    break;

                case ActionType.WORKFLOW_STEP:
                    await handleWorkflowStep(action);
                    break;

                case ActionType.CONTACT_SUPPORT:
                    handleContactSupport();
                    break;

                case ActionType.REFINE_QUERY:
                    // This is handled in the chat UI itself
                    toast.info("Please refine your query with more details");
                    break;

                case ActionType.VIEW_EXTERNAL:
                    handleViewExternal(action);
                    break;

                default:
                    console.warn(`Unknown action type: ${action.action_type}`);
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
     * Handle SAVE_TOOL action - save custom tool YAML
     */
    async function handleSaveTool(action: ActionSuggestion, agentResponse: AgentResponse) {
        const toolYaml = agentResponse.metadata.tool_yaml || action.parameters.tool_yaml;
        const toolId = agentResponse.metadata.tool_id || action.parameters.tool_id;

        if (!toolYaml) {
            toast.error("No tool YAML provided for save action");
            return;
        }

        // Show modal for saving tool
        toolModalContent.value = {
            type: "save",
            yaml: toolYaml,
            toolId: toolId,
            toolName: agentResponse.metadata.tool_name,
        };
        showToolModal.value = true;
    }

    /**
     * Handle TEST_TOOL action - open tool testing interface
     */
    async function handleTestTool(action: ActionSuggestion, agentResponse: AgentResponse) {
        const toolId = agentResponse.metadata.tool_id || action.parameters.tool_id;

        if (!toolId) {
            toast.error("No tool ID provided for test action");
            return;
        }

        // Show modal for testing tool
        toolModalContent.value = {
            type: "test",
            toolId: toolId,
            toolName: agentResponse.metadata.tool_name,
            yaml: agentResponse.metadata.tool_yaml,
        };
        showToolModal.value = true;
    }

    /**
     * Handle PARAMETER_CHANGE action - highlight parameter with suggestion
     */
    async function handleParameterChange(action: ActionSuggestion) {
        const toolId = action.parameters.tool_id;
        const paramName = action.parameters.param_name;
        const suggestedValue = action.parameters.suggested_value;

        if (!toolId || !paramName) {
            toast.error("Incomplete parameter change information");
            return;
        }

        // Navigate to tool with highlighted parameter
        router.push({
            path: "/",
            query: {
                tool_id: toolId,
                highlight_param: paramName,
                suggested_value: suggestedValue,
            },
        });

        toast.info(`Suggestion: Change '${paramName}' to '${suggestedValue}'`);
    }

    /**
     * Handle WORKFLOW_STEP action - navigate to workflow editor
     */
    async function handleWorkflowStep(action: ActionSuggestion) {
        const workflowId = action.parameters.workflow_id;
        const stepId = action.parameters.step_id;

        if (!workflowId) {
            toast.error("No workflow ID provided");
            return;
        }

        // Navigate to workflow editor
        const route = stepId
            ? `/workflows/editor?id=${workflowId}&highlight_step=${stepId}`
            : `/workflows/editor?id=${workflowId}`;

        router.push(route);
        toast.success("Opening workflow editor");
    }

    /**
     * Handle CONTACT_SUPPORT action
     */
    function handleContactSupport() {
        window.open("https://galaxyproject.org/support/", "_blank");
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
        toast.success("Opening tutorial in new tab");
    }

    /**
     * Save tool YAML to user's collection
     */
    async function saveToolToCollection(yaml: string, toolId: string) {
        try {
            const response = await fetch(`${getAppRoot()}api/agent_tools/save`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    yaml_content: yaml,
                    tool_id: toolId,
                    activate: true,
                }),
            });

            const result = await response.json();
            if (result.success) {
                toast.success(`Tool '${toolId}' saved successfully!`);
                showToolModal.value = false;

                // Refresh tool panel
                window.dispatchEvent(new Event("refresh-tool-panel"));

                return true;
            } else {
                toast.error(`Failed to save tool: ${result.errors?.join(", ")}`);
                return false;
            }
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : String(error);
            toast.error(`Error saving tool: ${errorMessage}`);

            return false;
        }
    }

    /**
     * Get action icon based on type
     */
    function getActionIcon(actionType: ActionType): string {
        const icons = {
            [ActionType.TOOL_RUN]: "🔧",
            [ActionType.SAVE_TOOL]: "💾",
            [ActionType.TEST_TOOL]: "🧪",
            [ActionType.PARAMETER_CHANGE]: "⚙️",
            [ActionType.WORKFLOW_STEP]: "📊",
            [ActionType.CONTACT_SUPPORT]: "🆘",
            [ActionType.REFINE_QUERY]: "✏️",
            [ActionType.VIEW_EXTERNAL]: "🔗",
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
        showToolModal,
        toolModalContent,
        handleAction,
        saveToolToCollection,
        getActionIcon,
        getActionVariant,
    };
}
