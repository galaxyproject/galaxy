<script setup lang="ts">
import type { IconDefinition } from "@fortawesome/fontawesome-svg-core";
import {
    faBug,
    faClock,
    faGraduationCap,
    faHistory,
    faMagic,
    faMicroscope,
    faPaperPlane,
    faPlus,
    faRobot,
    faRoute,
    faThumbsDown,
    faThumbsUp,
    faTrash,
    faUser,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BSkeleton } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";

import { GalaxyApi } from "@/api";
import { type ActionSuggestion, type AgentResponse, useAgentActions } from "@/composables/agentActions";
import { useMarkdown } from "@/composables/markdown";
import { useToast } from "@/composables/toast";
import { useHistoryDatasets } from "@/composables/useHistoryDatasets";
import {
    type PyodideArtifact,
    type PyodideRunResult,
    type PyodideTask,
    usePyodideRunner,
} from "@/composables/usePyodideRunner";
import { getAppRoot } from "@/onload/loadConfig";
import { useHistoryStore } from "@/stores/historyStore";
import { errorMessageAsString } from "@/utils/simple-error";

import type { AnalysisStep, ChatHistoryItem, ExecutionState, Message, UploadedArtifact } from "./ChatGXY/types";
import type { DataOption } from "./Form/Elements/FormData/types";

import ActionCard from "./ChatGXY/ActionCard.vue";
import DatasetSelector from "./Form/Elements/FormData/FormData.vue";
import Heading from "@/components/Common/Heading.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import UtcDate from "@/components/UtcDate.vue";

const query = ref("");
const messages = ref<Message[]>([]);
const errorMessage = ref("");
const busy = ref(false);
const chatContainer = ref<HTMLElement>();
const selectedAgentType = ref("auto");
const showHistory = ref(false);
const chatHistory = ref<ChatHistoryItem[]>([]);
const loadingHistory = ref(false);
const currentChatId = ref<number | null>(null);
const hasLoadedInitialChat = ref(false);
const pendingCollapsedMessages: Message[] = [];

const selectedDatasets = ref<string[]>([]);
/** A computed ref that gets/sets the selected datasets as `FormData` structured data,
 * based on the `selectedDatasets` array of IDs.
 *
 * TODO: Fix a major bug here with multiselect, somehow, in column select, when we select/deselect all,
 * the counts do not update correctly. Possibly related to how the options are built?
 */
const selectedDatasetsFormData = computed<{
    values: Array<DataOption>;
} | null>({
    get() {
        if (selectedDatasets.value.length === 0) {
            return null;
        }
        const selected = datasetOptions.value.filter((dataset) => selectedDatasets.value.includes(dataset.id));
        return {
            values: selected,
        };
    },
    set(value) {
        if (value === null) {
            selectedDatasets.value = [];
        } else {
            selectedDatasets.value = value.values.map((dataset) => dataset.id);
        }
    },
});
/** `FormData` structured options for datasets */
const formDataOptions = computed<Record<string, Array<DataOption>>>(() => ({ hda: datasetOptions.value }));

const { currentHistoryId } = storeToRefs(useHistoryStore());

/** Whether fetching datasets is allowed/enabled (for Data Analysis agent type) */
const allowFetchingDatasets = ref(false);

// History items variables
const {
    datasets: currentHistoryDatasets,
    isFetching: loadingDatasets,
    error: datasetError,
    // initialFetchDone: initialFetch, // TODO: Remove if we don't need this
} = useHistoryDatasets({
    historyId: () => currentHistoryId.value || "",
    enabled: () => currentHistoryId.value !== null && allowFetchingDatasets.value,
});

const datasetOptions = computed<DataOption[]>(() => {
    if (loadingDatasets.value) {
        return [];
    }
    const datasets = currentHistoryDatasets.value;

    return datasets
        .map((item) => {
            const name = item.name || `Dataset ${item.hid || ""}`;
            const hidden = Boolean(item.visible === false);
            const generated = typeof name === "string" && name.trim().toLowerCase().startsWith("generated_file");
            if (!item.id || hidden || generated) {
                return null;
            }
            // TODO: We aren't using `file_size` key in `useHistoryDatasets` currently
            //       Neither are we storing the extensions for the datasets.
            return {
                id: item.id,
                hid: item.hid,
                name,
                src: "hda",
            } as DataOption;
        })
        .filter((entry): entry is DataOption => entry !== null && Boolean(entry));
});

// Ensure selected datasets are valid when dataset options change
watch(
    () => datasetOptions.value,
    () => {
        const validIds = new Set(datasetOptions.value.map((entry) => entry.id));
        selectedDatasets.value = selectedDatasets.value.filter((id) => validIds.has(id));
    },
    { immediate: true, deep: true },
);

const toast = useToast();
const pyodideRunner = usePyodideRunner();
const pyodideExecutions = reactive<Record<string, ExecutionState>>({});
const chatStream = ref<WebSocket | null>(null);
const streamSupported = typeof window !== "undefined" && typeof WebSocket !== "undefined";
const deliveredTaskIds = new Set<string>();
const pyodideTaskToMessage = new Map<string, Message>();
const isChatBusy = computed(
    () => busy.value || pyodideRunner.isRunning.value || messages.value.some((message) => isAwaitingExecution(message)),
);

const { renderMarkdown } = useMarkdown({ openLinksInNewPage: true, removeNewlinesAfterList: true });
const { processingAction, handleAction } = useAgentActions();

function escapeHtml(raw: string): string {
    // Minimal escaping for fallback rendering.
    return raw
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

function safeRenderMarkdown(content: unknown): string {
    const text = typeof content === "string" ? content : String(content ?? "");
    try {
        return renderMarkdown(text);
    } catch (error) {
        console.error("Failed to render markdown for chat message:", error);
        return `<pre>${escapeHtml(text)}</pre>`;
    }
}

function normaliseSuggestions(raw: unknown): ActionSuggestion[] {
    return Array.isArray(raw) ? (raw as ActionSuggestion[]) : [];
}

interface AgentType {
    value: string;
    label: string;
    icon: IconDefinition;
    description: string;
}

const agentTypes: AgentType[] = [
    { value: "auto", label: "Auto (Router)", icon: faMagic, description: "Intelligent routing" },
    { value: "router", label: "Router", icon: faRoute, description: "Query router" },
    { value: "error_analysis", label: "Error Analysis", icon: faBug, description: "Debug tool errors" },
    { value: "custom_tool", label: "Custom Tool", icon: faPlus, description: "Create custom tools" },
    {
        value: "data_analysis",
        label: "Data Analysis",
        icon: faMicroscope,
        description: "Explore datasets with generated code",
    },
    // { value: "data_analysis_dspy", label: "📊 Data Analysis (DSPy)", description: "Iterative planning with DSPy + auto code execution" },
    { value: "gtn_training", label: "GTN Training", icon: faGraduationCap, description: "Find tutorials" },
];

// Map agent types to their icons for quick lookup
const agentIconMap: Record<string, IconDefinition> = {
    auto: faMagic,
    router: faRoute,
    error_analysis: faBug,
    custom_tool: faPlus,
    data_analysis: faMicroscope,
    gtn_training: faGraduationCap,
};

onMounted(async () => {
    // Try to load the most recent chat
    await loadLatestChat();

    // TODO: This should be conditionally set only for the Data Analysis agent type
    allowFetchingDatasets.value = true;

    // If no chat was loaded, show the welcome message
    if (!hasLoadedInitialChat.value) {
        messages.value.push({
            id: generateId(),
            role: "assistant",
            content:
                "👋 Welcome to ChatGXY! I can help you with:\n\n" +
                "• **Finding the right tools** for your analysis\n" +
                "• **Debugging errors** in your workflows\n" +
                "• **Optimizing performance** of your pipelines\n" +
                "• **Checking data quality** issues\n\n" +
                "Just ask me anything about Galaxy and I'll route your question to the right specialist!",
            timestamp: new Date(),
            agentType: "router",
            confidence: "high",
            feedback: null,
            isSystemMessage: true,
        });
    }
});

watch(
    () => currentHistoryId.value,
    () => {
        selectedDatasets.value = [];
    },
    { immediate: false },
);

function generateId() {
    return `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

function applyDatasetSelectionFromMessages(conversation: any[]) {
    for (let i = conversation.length - 1; i >= 0; i -= 1) {
        const entry = conversation[i];
        const datasets = entry?.dataset_ids;
        if (Array.isArray(datasets) && datasets.length > 0) {
            selectedDatasets.value = datasets.map(String);
            return;
        }
    }
}

function attachPendingCollapsedMessages(target: Message) {
    if (!pendingCollapsedMessages.length) {
        return;
    }
    target.collapsedHistory = pendingCollapsedMessages.map((msg) => {
        msg.isCollapsed = true;
        return msg;
    });
    for (let i = pendingCollapsedMessages.length - 1; i >= 0; i -= 1) {
        const msg = pendingCollapsedMessages[i];

        if (msg) {
            if (!target.generatedPlots?.length && msg.generatedPlots?.length) {
                target.generatedPlots = [...msg.generatedPlots];
            }
            if (!target.generatedFiles?.length && msg.generatedFiles?.length) {
                target.generatedFiles = [...msg.generatedFiles];
            }
            if ((!target.artifacts || !target.artifacts.length) && msg.artifacts?.length) {
                target.artifacts = [...msg.artifacts];
            }
        }
    }
    if (target.isCollapsed === undefined) {
        target.isCollapsed = true;
    }
    pendingCollapsedMessages.length = 0;
}

function getLatestUserQuery(): string {
    for (let i = messages.value.length - 1; i >= 0; i -= 1) {
        const entry = messages.value[i];
        if (entry?.role === "user") {
            return entry.content;
        }
    }
    return "";
}

function findMessageForPayload(payload: any): Message | undefined {
    const candidateTaskId =
        payload?.task_id ||
        payload?.pyodide_task_id ||
        payload?.agent_response?.metadata?.executed_task?.task_id ||
        payload?.agent_response?.metadata?.pyodide_task?.task_id;
    if (candidateTaskId) {
        const key = String(candidateTaskId);
        if (pyodideTaskToMessage.has(key)) {
            return pyodideTaskToMessage.get(key);
        }
        const fallback = messages.value.find((message) => {
            const metadata = message.agentResponse?.metadata as Record<string, any> | undefined;
            if (!metadata) {
                return false;
            }
            const executedTask = metadata.executed_task;
            const pendingTask = metadata.pyodide_task;
            return (
                (executedTask && String(executedTask.task_id) === key) ||
                (pendingTask && String(pendingTask.task_id) === key)
            );
        });
        if (fallback) {
            pyodideTaskToMessage.set(key, fallback);
            return fallback;
        }
    }
    return undefined;
}

function shouldAutoCollapse(message: Message): boolean {
    if (message.role !== "assistant") {
        return false;
    }
    if (isAwaitingExecution(message)) {
        return false;
    }
    const metadata = message.agentResponse?.metadata as Record<string, any> | undefined;
    if (!metadata) {
        return false;
    }
    if (metadata.is_complete === true) {
        return false;
    }
    if (metadata.executed_task || metadata.execution || metadata.pyodide_status === "completed") {
        return true;
    }
    if (metadata.pyodide_status === "error" || metadata.pyodide_status === "timeout") {
        return true;
    }
    return false;
}

function applyCollapseState(message: Message) {
    const collapsible = shouldAutoCollapse(message);
    message.isCollapsible = collapsible;
    if (!collapsible) {
        delete message.isCollapsed;
        return;
    }
    if (message.isCollapsed === undefined) {
        message.isCollapsed = true;
    }
}

function collapsedSummary(message: Message): string {
    const metadata = message.agentResponse?.metadata as Record<string, any> | undefined;
    if (metadata?.summary && typeof metadata.summary === "string") {
        return metadata.summary;
    }
    const content = (message.content || "").trim();
    return content.split("\n")[0] || "Previous step";
}

function handleIntermediateToggle(event: Event, message: Message) {
    const details = event.target as HTMLDetailsElement | null;
    if (!details) {
        return;
    }
    message.isCollapsed = !details.open;
}

function isDataAnalysisMessage(message?: Message): boolean {
    if (!message) {
        return false;
    }
    const agentType = message.agentType || message.agentResponse?.agent_type;
    return typeof agentType === "string" && agentType.startsWith("data_analysis");
}

function populateAssistantMessage(
    target: Message,
    payload: any,
    fallbackAgentType: string,
    options?: { skipDatasetUpdate?: boolean },
) {
    const agentResponse = (payload?.agent_response ?? payload?.response?.agent_response) as AgentResponse | undefined;
    const rawContent =
        typeof payload === "string" ? payload : (payload?.response ?? agentResponse?.content ?? "No response received");
    const content = typeof rawContent === "string" ? rawContent : String(rawContent ?? "No response received");
    const effectiveAgentType =
        agentResponse?.agent_type || (fallbackAgentType === "auto" ? "router" : fallbackAgentType);

    target.content = content;
    target.timestamp = payload?.timestamp ? new Date(payload.timestamp) : new Date();
    target.agentType = effectiveAgentType;
    target.confidence = agentResponse?.confidence || (payload?.confidence as string) || "medium";
    target.feedback = target.feedback ?? null;
    target.agentResponse = agentResponse;
    target.suggestions = normaliseSuggestions(agentResponse?.suggestions);
    target.routingInfo = payload?.routing_info;

    const metadata = agentResponse?.metadata as Record<string, unknown> | undefined;
    if (metadata) {
        const steps = normaliseAnalysisSteps((metadata as any)?.analysis_steps);
        if (steps.length) {
            target.analysisSteps = steps;
        }
        const artifactSource = (metadata as any)?.artifacts ?? (metadata as any)?.execution?.artifacts;
        const storedArtifacts = normaliseArtifactList(artifactSource);
        updateMessageOutputsFromArtifacts(target, storedArtifacts);
        const plotEntries = normalisePathList((metadata as any)?.plots);
        if (plotEntries.length) {
            target.generatedPlots = plotEntries;
        }
        const fileEntries = normalisePathList((metadata as any)?.files);
        if (fileEntries.length) {
            target.generatedFiles = fileEntries;
        }
        const executedTask = (metadata as any)?.executed_task;
        if (executedTask?.task_id) {
            const taskId = String(executedTask.task_id);
            deliveredTaskIds.add(taskId);
            pyodideTaskToMessage.set(taskId, target);
        }
        const pendingTask = (metadata as any)?.pyodide_task;
        if (pendingTask?.task_id) {
            pyodideTaskToMessage.set(String(pendingTask.task_id), target);
        }
    }

    if (!options?.skipDatasetUpdate) {
        if (Array.isArray(payload?.dataset_ids) && payload.dataset_ids.length > 0) {
            selectedDatasets.value = payload.dataset_ids.map(String);
        }
    }

    applyCollapseState(target);
}

function appendAssistantMessage(payload: any, fallbackAgentType: string): Message {
    const existingMessage = findMessageForPayload(payload);
    if (existingMessage) {
        populateAssistantMessage(existingMessage, payload, fallbackAgentType, { skipDatasetUpdate: true });
        if (!existingMessage.isCollapsible) {
            attachPendingCollapsedMessages(existingMessage);
        }
        maybeRunPyodideForMessage(existingMessage);
        return existingMessage;
    }

    const assistantMessage: Message = {
        id: generateId(),
        role: "assistant",
        content: "",
        timestamp: new Date(),
        agentType: fallbackAgentType === "auto" ? "router" : fallbackAgentType,
        confidence: "medium",
        feedback: null,
    };

    populateAssistantMessage(assistantMessage, payload, fallbackAgentType);

    if (assistantMessage.isCollapsible) {
        pendingCollapsedMessages.push(assistantMessage);
        return assistantMessage;
    }

    attachPendingCollapsedMessages(assistantMessage);

    messages.value.push(assistantMessage);

    if (payload?.exchange_id) {
        currentChatId.value = payload.exchange_id;
    }

    maybeRunPyodideForMessage(assistantMessage);
    ensurePendingPyodideTasks();

    return assistantMessage;
}

function maybeRunPyodideForMessage(message: Message) {
    const metadata = message.agentResponse?.metadata as Record<string, any> | undefined;
    if (!metadata) {
        return;
    }
    const task = metadata.pyodide_task as PyodideTask | undefined;
    if (!task) {
        return;
    }
    const taskKey = task.task_id || message.id;
    if (task.task_id) {
        pyodideTaskToMessage.set(String(task.task_id), message);
    }
    if (task.task_id && deliveredTaskIds.has(task.task_id)) {
        metadata.pyodide_status = metadata.pyodide_status || "completed";
        return;
    }
    const existing = pyodideExecutions[taskKey];
    if (existing) {
        // Do not retry if we have already completed or errored out.
        if (existing.status === "completed" || existing.status === "error") {
            metadata.pyodide_status = existing.status;
            return;
        }
        return;
    }

    const status = metadata.pyodide_status as string | undefined;
    if (status === "error" || status === "completed" || status === "timeout") {
        delete metadata.pyodide_task;
        const baseState: ExecutionState = {
            status: status === "completed" ? "completed" : "error",
            stdout: metadata.stdout || "",
            stderr: metadata.stderr || "",
            artifacts: [],
        };
        if (status === "error") {
            baseState.errorMessage = metadata.error || "";
        } else if (status === "timeout") {
            baseState.errorMessage =
                metadata.pyodide_timeout_reason ||
                `Execution timed out after ${metadata.pyodide_timeout_seconds || "unknown"} seconds.`;
        }
        pyodideExecutions[taskKey] = baseState;
        return;
    }
    if (status && status !== "pending") {
        return;
    }

    if (!pyodideRunner.isSupported.value) {
        pyodideExecutions[taskKey] = {
            status: "error",
            stdout: "",
            stderr: "",
            artifacts: [],
            errorMessage: "Browser does not support in-browser execution.",
        };
        metadata.pyodide_status = "error";
        toast.warning("This browser cannot run the generated analysis code.");
        return;
    }

    metadata.pyodide_retry_count = (metadata.pyodide_retry_count || 0) + 1;
    if (metadata.pyodide_retry_count > 1) {
        metadata.pyodide_status = "error";
        pyodideExecutions[taskKey] = {
            status: "error",
            stdout: "",
            stderr: "",
            artifacts: [],
            errorMessage: "Pyodide task exceeded retry limit.",
        };
        return;
    }

    runPyodideTaskForMessage(message, task, taskKey, metadata);
}

function ensurePendingPyodideTasks() {
    messages.value.forEach((message) => {
        const metadata = message.agentResponse?.metadata as Record<string, any> | undefined;
        if (!metadata) {
            return;
        }
        const task = metadata.pyodide_task as PyodideTask | undefined;
        if (!task) {
            return;
        }
        const status = (metadata.pyodide_status as string | undefined) || "pending";
        if (status === "error" || status === "completed" || status === "timeout") {
            return;
        }
        const taskKey = task.task_id || message.id;
        if (pyodideExecutions[taskKey]) {
            return;
        }
        if (task.task_id && deliveredTaskIds.has(task.task_id)) {
            return;
        }
        maybeRunPyodideForMessage(message);
    });
}

watch(
    messages,
    () => {
        ensurePendingPyodideTasks();
    },
    { deep: true },
);

function runPyodideTaskForMessage(message: Message, task: PyodideTask, taskKey: string, metadata: Record<string, any>) {
    const state = reactive<ExecutionState>({
        status: "initialising",
        stdout: "",
        stderr: "",
        artifacts: [],
    });
    pyodideExecutions[taskKey] = state;
    metadata.pyodide_status = "running";

    const runnerTask: PyodideTask = { ...task, task_id: taskKey };

    let executionPromise: Promise<any>;
    try {
        // `runTask` may throw synchronously (e.g. Worker construction failures). Make
        // sure we surface the error instead of taking down the whole chat UI.
        executionPromise = pyodideRunner.runTask(runnerTask, {
            onStdout: (line) => {
                state.stdout += line;
            },
            onStderr: (line) => {
                state.stderr += line;
            },
            onStatus: (event) => {
                state.status = mapStatus(event.status);
            },
        });
    } catch (error) {
        const errMessage = error instanceof Error ? error.message : String(error);
        state.status = "error";
        state.errorMessage = errMessage;
        metadata.pyodide_status = "error";
        if (metadata.pyodide_task) {
            delete metadata.pyodide_task;
        }
        toast.error(`Pyodide execution failed: ${errMessage}`);
        return;
    }

    executionPromise
        .then(async (result) => {
            state.stdout = result.stdout;
            state.stderr = result.stderr;
            state.status = "submitting";
            let uploadedArtifacts: UploadedArtifact[] = [];
            try {
                uploadedArtifacts = await uploadArtifacts(result.artifacts || []);
                state.artifacts = uploadedArtifacts;
                updateMessageOutputsFromArtifacts(message, uploadedArtifacts);
                await submitPyodideExecutionResult(runnerTask, message, result, uploadedArtifacts);
                applyExecutionResultMetadata(message, {
                    success: result.success,
                    stdout: result.stdout,
                    stderr: result.stderr,
                    artifacts: serializeUploadedArtifacts(uploadedArtifacts),
                    task_id: runnerTask.task_id,
                });
                state.status = result.success ? "completed" : "error";
                if (!result.success && result.error) {
                    state.errorMessage = result.error;
                }
                metadata.pyodide_status = state.status;
            } catch (error) {
                const errMessage = error instanceof Error ? error.message : String(error);
                state.status = "error";
                state.errorMessage = errMessage;
                metadata.pyodide_status = "error";
                if (metadata.pyodide_task) {
                    delete metadata.pyodide_task;
                }
                toast.error(`Pyodide execution failed: ${errMessage}`);
            }
        })
        .catch((error) => {
            const errMessage = error instanceof Error ? error.message : String(error);
            if (error && (error as any).stdout && typeof (error as any).stdout === "string") {
                state.stdout += (error as any).stdout;
            }
            if (error && (error as any).stderr && typeof (error as any).stderr === "string") {
                state.stderr += (error as any).stderr;
            }
            state.status = "error";
            state.errorMessage = errMessage;
            metadata.pyodide_status = "error";
            if (metadata.pyodide_task) {
                delete metadata.pyodide_task;
            }
            toast.error(`Pyodide execution failed: ${errMessage}`);
        });
}
function openChatStream(exchangeId: number) {
    if (!streamSupported) {
        return;
    }
    const existing = chatStream.value;
    if (existing) {
        const existingId = (existing as any)._exchangeId as number | undefined;
        if (
            existingId === exchangeId &&
            (existing.readyState === WebSocket.OPEN || existing.readyState === WebSocket.CONNECTING)
        ) {
            return;
        }
        existing.close();
    }

    try {
        const rawRoot = getAppRoot() || "/";
        const appRoot = rawRoot.replace(/\/+$/, "") || "/";
        const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        const wsUrl = `${protocol}//${window.location.host}${appRoot}/api/chat/exchange/${exchangeId}/stream`;
        const socket = new WebSocket(wsUrl);
        (socket as any)._exchangeId = exchangeId;
        socket.onopen = () => {
            chatStream.value = socket;
        };
        socket.onmessage = (event: MessageEvent) => {
            handleStreamMessage(event);
        };
        socket.onclose = () => {
            if (chatStream.value === socket) {
                chatStream.value = null;
            }
        };
        socket.onerror = () => {
            socket.close();
        };
    } catch (error) {
        console.error("Failed to open chat stream", error);
    }
}

function closeChatStream() {
    const socket = chatStream.value;
    if (socket) {
        chatStream.value = null;
        try {
            socket.close();
        } catch (error) {
            console.error("Failed to close chat stream", error);
        }
    }
}

function handleStreamMessage(event: MessageEvent) {
    try {
        const payload = JSON.parse(event.data);
        if (payload?.type === "exec_followup" && payload.payload) {
            if (payload.exchange_id && payload.exchange_id !== currentChatId.value) {
                return;
            }
            const taskId = payload.task_id as string | undefined;
            if (taskId && deliveredTaskIds.has(taskId)) {
                return;
            }
            if (taskId) {
                deliveredTaskIds.add(taskId);
                const existing = pyodideTaskToMessage.get(String(taskId));
                if (existing) {
                    populateAssistantMessage(existing, payload.payload, selectedAgentType.value, {
                        skipDatasetUpdate: true,
                    });
                    maybeRunPyodideForMessage(existing);
                    return;
                }
            }
            appendAssistantMessage(payload.payload, selectedAgentType.value);
        }
    } catch (error) {
        console.error("Failed to process chat stream message", error);
    }
}

async function uploadArtifacts(artifacts: PyodideArtifact[]): Promise<UploadedArtifact[]> {
    if (!currentChatId.value) {
        throw new Error("No active chat to attach artifacts.");
    }
    if (!artifacts || artifacts.length === 0) {
        return [];
    }

    const results: UploadedArtifact[] = [];
    for (const artifact of artifacts) {
        const buffer = artifact.buffer;
        if (!buffer) {
            continue;
        }
        const blob = new Blob([buffer], { type: artifact.mime_type || "application/octet-stream" });
        if (blob.size === 0) {
            continue;
        }
        const formData = new FormData();
        formData.append("file", blob, artifact.name || "artifact");
        if (artifact.name) {
            formData.append("name", artifact.name);
        }
        formData.append("mime_type", artifact.mime_type || blob.type || "application/octet-stream");
        formData.append("size", String(blob.size));

        const response = await fetch(`${getAppRoot()}api/chat/exchange/${currentChatId.value}/artifacts`, {
            method: "POST",
            body: formData,
            credentials: "include",
        });

        if (!response.ok) {
            const errorText = await response.text();
            const description = errorText || response.statusText || "Unknown error";
            throw new Error(`Artifact upload failed (${response.status}): ${description}`);
        }

        const payload = (await response.json()) as UploadedArtifact;
        if (payload.download_url) {
            payload.download_url = resolveDownloadUrl(payload.download_url);
        }
        results.push(payload);
        artifact.buffer = undefined;
    }
    return results;
}

function resolveDownloadUrl(url: string): string {
    if (!url) {
        return url;
    }
    if (/^https?:\/\//i.test(url)) {
        return url;
    }
    const rootCandidate = getAppRoot() || window.location.origin;
    const absoluteRoot = rootCandidate.replace(/\/$/, "");
    if (url.startsWith("/")) {
        return `${absoluteRoot}${url}`;
    }
    return `${getAppRoot()}${url}`;
}

function mapStatus(status: string): ExecutionState["status"] {
    switch (status) {
        case "initialising":
            return "initialising";
        case "installing":
            return "installing";
        case "fetch":
            return "fetching";
        case "executing":
            return "running";
        case "collecting":
            return "submitting";
        default:
            return "running";
    }
}

async function submitPyodideExecutionResult(
    task: PyodideTask,
    message: Message,
    result: PyodideRunResult,
    artifacts: UploadedArtifact[],
) {
    if (!currentChatId.value) {
        throw new Error("No active chat to submit execution results.");
    }

    const useStream = streamSupported && chatStream.value?.readyState === WebSocket.OPEN;

    const payload = {
        task_id: task.task_id,
        stdout: result.stdout,
        stderr: result.stderr,
        artifacts,
        success: result.success,
        metadata: {
            selected_dataset_ids: [...selectedDatasets.value],
            agent_type: message.agentResponse?.agent_type || message.agentType,
            original_query: getLatestUserQuery(),
        },
    };

    // @ts-ignore TODO: We will add the pydantic model later
    const { data, error } = await GalaxyApi().POST(`/api/chat/exchange/${currentChatId.value}/pyodide_result`, {
        body: payload,
    });

    if (error) {
        throw new Error(errorMessageAsString(error, "Failed to submit execution results"));
    }

    if (!useStream && data) {
        if (payload.task_id) {
            deliveredTaskIds.add(payload.task_id);
        }
        appendAssistantMessage(data, message.agentType || selectedAgentType.value);
    }
}

function pyodideStateForMessage(message: Message): ExecutionState | undefined {
    const metadata = message.agentResponse?.metadata as Record<string, any> | undefined;
    if (!metadata?.pyodide_task) {
        return undefined;
    }
    const task = metadata.pyodide_task as PyodideTask;
    const key = task.task_id || message.id;
    return pyodideExecutions[key];
}

function shouldShowPyodideStatus(message: Message): boolean {
    return Boolean(pyodideStateForMessage(message));
}

function hasIntermediateDetails(message: Message): boolean {
    const metadata = message.agentResponse?.metadata as Record<string, any> | undefined;
    if (metadata?.executed_task?.code || metadata?.stdout || metadata?.stderr) {
        return true;
    }
    if (message.analysisSteps?.length) {
        return true;
    }
    if (pyodideStateForMessage(message)) {
        return true;
    }
    return false;
}

watch(
    currentChatId,
    (newId, oldId) => {
        if (!streamSupported) {
            return;
        }
        if (oldId && newId !== oldId) {
            closeChatStream();
            deliveredTaskIds.clear();
        }
        if (typeof newId === "number") {
            openChatStream(newId);
        }
        if (newId == null) {
            deliveredTaskIds.clear();
        }
    },
    { immediate: false },
);
onBeforeUnmount(() => {
    closeChatStream();
});

function downloadArtifact(artifact: UploadedArtifact) {
    if (artifact.download_url) {
        window.open(artifact.download_url, "_blank");
        return;
    }
    toast.info("Artifact download is not available yet.");
}

function formatSize(size?: number): string {
    if (size === undefined || size === null) {
        return "";
    }
    if (size < 1024) {
        return `${size} B`;
    }
    const units = ["KB", "MB", "GB", "TB"];
    let value = size / 1024;
    let unitIndex = 0;
    while (value >= 1024 && unitIndex < units.length - 1) {
        value /= 1024;
        unitIndex += 1;
    }
    return `${value.toFixed(1)} ${units[unitIndex]}`;
}

function normalisePathList(raw: unknown): string[] {
    if (!Array.isArray(raw)) {
        return [];
    }
    const results: string[] = [];
    const seen = new Set<string>();
    for (const entry of raw) {
        const text = String(entry ?? "").trim();
        if (!text) {
            continue;
        }
        const normalised = text.startsWith("generated_file") ? text : `generated_file/${text.replace(/^\/+/, "")}`;
        if (!seen.has(normalised)) {
            seen.add(normalised);
            results.push(normalised);
        }
    }
    return results;
}

function normaliseArtifactList(raw: unknown): UploadedArtifact[] {
    if (!Array.isArray(raw)) {
        return [];
    }
    const artifacts: UploadedArtifact[] = [];
    for (const entry of raw) {
        if (!entry || typeof entry !== "object") {
            continue;
        }
        const record = entry as Record<string, any>;
        const identifier = record.dataset_id || record.name || record.path || record.id || generateId();
        const downloadUrl = record.download_url ? resolveDownloadUrl(String(record.download_url)) : undefined;
        artifacts.push({
            dataset_id: String(identifier),
            name: record.name ? String(record.name) : undefined,
            size: typeof record.size === "number" ? record.size : Number(record.size) || undefined,
            mime_type: record.mime_type ? String(record.mime_type) : undefined,
            download_url: downloadUrl || "",
            history_id: record.history_id ? String(record.history_id) : undefined,
        });
    }
    return artifacts;
}

// Commented out unused functions for now

// function normaliseGeneratedEntry(entry: string): string {
//     return entry.replace(/^generated_file\//, "").replace(/^\/+/, "");
// }

// function findArtifactForEntry(entry: string, artifacts?: UploadedArtifact[]): UploadedArtifact | undefined {
//     if (!artifacts || artifacts.length === 0) {
//         return undefined;
//     }
//     const normalized = normaliseGeneratedEntry(entry);
//     return artifacts.find((artifact) => {
//         const artifactName = normaliseGeneratedEntry(artifact.name || "");
//         return (
//             artifactName === normalized ||
//             artifactName === entry ||
//             artifact.dataset_id === normalized ||
//             artifact.dataset_id === entry
//         );
//     });
// }

// function artifactPreviewUrl(entry: string, artifacts?: UploadedArtifact[]): string | undefined {
//     const match = findArtifactForEntry(entry, artifacts);
//     return match?.download_url || undefined;
// }

// function artifactDownloadHandler(entry: string, artifacts?: UploadedArtifact[]) {
//     const match = findArtifactForEntry(entry, artifacts);
//     if (match) {
//         downloadArtifact(match);
//     }
// }

function formatGeneratedEntry(entry: string): string {
    return entry.replace(/^generated_file\//, "");
}

// function artifactIsDownloadable(entry: string, artifacts?: UploadedArtifact[]): boolean {
//     return Boolean(findArtifactForEntry(entry, artifacts));
// }

function updateMessageOutputsFromArtifacts(message: Message, artifacts: UploadedArtifact[] | undefined) {
    if (!artifacts || artifacts.length === 0) {
        return;
    }
    message.artifacts = artifacts;
    const plotNames: string[] = [];
    const fileNames: string[] = [];
    for (const artifact of artifacts) {
        const name = formatGeneratedEntry(artifact.name || artifact.dataset_id || "");
        if (!name) {
            continue;
        }
        if (artifact.mime_type && artifact.mime_type.startsWith("image/")) {
            plotNames.push(`generated_file/${name}`);
        } else {
            fileNames.push(`generated_file/${name}`);
        }
    }
    message.generatedPlots = plotNames.length ? plotNames : message.generatedPlots;
    message.generatedFiles = fileNames.length ? fileNames : message.generatedFiles;
}
function serializeUploadedArtifacts(artifacts: UploadedArtifact[] = []): any[] {
    return artifacts.map((artifact) => ({
        dataset_id: artifact.dataset_id,
        name: artifact.name,
        size: artifact.size,
        mime_type: artifact.mime_type,
        download_url: artifact.download_url,
        history_id: artifact.history_id,
    }));
}

function applyExecutionResultMetadata(message: Message, execResult: any) {
    if (!execResult) {
        return;
    }
    if (!message.agentResponse) {
        message.agentResponse = {
            metadata: {},
            suggestions: [],
            agent_type: message.agentType,
            confidence: message.confidence,
            content: message.content,
        } as unknown as AgentResponse;
    }
    const metadata = ((message.agentResponse as any).metadata ||= {});
    metadata.pyodide_status = execResult.success ? "completed" : "error";
    metadata.stdout = execResult.stdout || "";
    metadata.stderr = execResult.stderr || "";
    metadata.execution = {
        success: execResult.success,
        stdout: execResult.stdout || "",
        stderr: execResult.stderr || "",
        artifacts: execResult.artifacts || [],
        task_id: execResult.task_id,
    };
    if (metadata.pyodide_task && execResult.task_id) {
        metadata.executed_task = metadata.executed_task || { task_id: execResult.task_id };
        metadata.executed_task.task_id = execResult.task_id;
        pyodideTaskToMessage.set(String(execResult.task_id), message);
        deliveredTaskIds.add(String(execResult.task_id));
    }
    if (metadata.pyodide_task) {
        delete metadata.pyodide_task;
    }
    const artifacts = normaliseArtifactList(execResult.artifacts);
    updateMessageOutputsFromArtifacts(message, artifacts);
    applyCollapseState(message);
}

function normaliseAnalysisSteps(raw: unknown): AnalysisStep[] {
    if (!Array.isArray(raw)) {
        return [];
    }

    return raw
        .map((step) => {
            if (!step || typeof step !== "object") {
                return null;
            }
            const record = step as Record<string, unknown>;
            const type = record.type;
            if (type !== "thought" && type !== "action" && type !== "observation" && type !== "conclusion") {
                return null;
            }
            const content = String(record.content ?? "");
            const requirements = Array.isArray(record.requirements)
                ? (record.requirements as unknown[]).map(String)
                : undefined;
            const statusValue = record.status;
            const status: AnalysisStep["status"] | undefined =
                statusValue === "running" || statusValue === "completed" || statusValue === "error"
                    ? statusValue
                    : undefined;
            const stdout = typeof record.stdout === "string" ? record.stdout : undefined;
            const stderr = typeof record.stderr === "string" ? record.stderr : undefined;
            const success = typeof record.success === "boolean" ? record.success : undefined;
            return {
                type,
                content,
                requirements,
                status: type === "action" ? (status ?? "pending") : undefined,
                stdout,
                stderr,
                success,
            } as AnalysisStep;
        })
        .filter((step): step is AnalysisStep => Boolean(step));
}

async function submitQuery() {
    if (isChatBusy.value) {
        return;
    }
    if (!query.value.trim()) {
        return;
    }
    pendingCollapsedMessages.length = 0;

    const userMessage: Message = {
        id: generateId(),
        role: "user",
        content: query.value,
        timestamp: new Date(),
        feedback: null,
    };

    messages.value.push(userMessage);
    const currentQuery = query.value;
    query.value = "";

    // Scroll to bottom after adding user message
    await nextTick();
    scrollToBottom();

    busy.value = true;
    errorMessage.value = "";

    try {
        const { data, error } = await GalaxyApi().POST("/api/chat", {
            params: {
                query: {
                    agent_type: selectedAgentType.value,
                },
            },
            body: {
                query: currentQuery,
                context: null,
                exchange_id: currentChatId.value,
                agent_type: selectedAgentType.value,
                dataset_ids: selectedDatasets.value,
            },
        });

        if (error) {
            errorMessage.value = errorMessageAsString(error, "Failed to get response from ChatGXY.");
            const errorMsg: Message = {
                id: generateId(),
                role: "assistant",
                content: `❌ Error: ${errorMessage.value}`,
                timestamp: new Date(),
                agentType: selectedAgentType.value,
                confidence: "low",
                feedback: null,
            };
            messages.value.push(errorMsg);

            // Scroll to bottom after adding error message
            await nextTick();
            scrollToBottom();
        } else if (data) {
            // Extract typed response fields
            const agentResponse = data.agent_response as AgentResponse | undefined;
            const content = data.response || "No response received";

            // Get the exchange ID if returned
            if (data.exchange_id) {
                currentChatId.value = data.exchange_id;
            }

            const assistantMessage: Message = {
                id: generateId(),
                role: "assistant",
                content: content,
                timestamp: new Date(),
                agentType:
                    agentResponse?.agent_type ||
                    (selectedAgentType.value === "auto" ? "router" : selectedAgentType.value),
                confidence: agentResponse?.confidence || "medium",
                feedback: null,
                agentResponse: agentResponse,
                suggestions: normaliseSuggestions(agentResponse?.suggestions),
            };
            messages.value.push(assistantMessage);

            // Scroll to bottom after adding assistant message
            await nextTick();
            scrollToBottom();
        }
    } catch (e) {
        errorMessage.value = `Unexpected error: ${e}`;
        const errorMsg: Message = {
            id: generateId(),
            role: "assistant",
            content: `❌ Unexpected error occurred. Please try again.`,
            timestamp: new Date(),
            agentType: selectedAgentType.value,
            confidence: "low",
            feedback: null,
        };
        messages.value.push(errorMsg);

        // Scroll to bottom after adding error message
        await nextTick();
        scrollToBottom();
    } finally {
        busy.value = false;
        await nextTick();
        scrollToBottom();
    }
}

function scrollToBottom() {
    if (chatContainer.value) {
        // Use smooth scrolling and avoid focus disruption
        chatContainer.value.scrollTo({
            top: chatContainer.value.scrollHeight,
            behavior: "auto", // Use 'smooth' if you want animated scrolling
        });
    }
}

// Scroll to bottom when busy state changes to show loading skeleton
watch(busy, (isBusy) => {
    if (isBusy) {
        nextTick(() => scrollToBottom());
    }
});

async function sendFeedback(messageId: string, value: "up" | "down") {
    const message = messages.value.find((m) => m.id === messageId);
    if (message) {
        // Update UI immediately
        message.feedback = value;

        // Only persist if we have a currentChatId (for saved chats)
        if (currentChatId.value) {
            try {
                const feedbackValue = value === "up" ? 1 : 0;

                // @ts-ignore TODO: Add pydantic model later
                const { error } = await GalaxyApi().PUT("/api/chat/exchange/{exchange_id}/feedback", {
                    params: {
                        path: { exchange_id: currentChatId.value },
                    },
                    body: feedbackValue,
                });

                if (error) {
                    console.error("Failed to save feedback:", error);
                    // Revert on error
                    message.feedback = null;
                }
            } catch (e) {
                console.error("Failed to save feedback:", e);
                // Revert on error
                message.feedback = null;
            }
        }
    }
}

function getAgentIcon(agentType?: string): IconDefinition {
    return agentIconMap[agentType || ""] || faRobot;
}

function getAgentLabel(agentType?: string) {
    const agent = agentTypes.find((a) => a.value === agentType);
    return agent?.label || agentType || "AI Assistant";
}

function formatModelName(model?: string): string {
    if (!model) {
        return "";
    }
    // Extract just the model name from full paths like "openai/gpt-4" or "anthropic/claude-3"
    const parts = model.split("/");
    return parts[parts.length - 1] || model;
}

function getAgentResponseOrEmpty(response?: AgentResponse): AgentResponse {
    return (
        response || ({ content: "", agent_type: "", confidence: "low", suggestions: [], metadata: {} } as AgentResponse)
    );
}

function isAwaitingExecution(message: Message): boolean {
    const metadata = message.agentResponse?.metadata as Record<string, unknown> | undefined;
    if (!metadata) {
        return false;
    }
    const status = typeof metadata.pyodide_status === "string" ? metadata.pyodide_status : undefined;
    return Boolean(status && status !== "completed" && status !== "error" && status !== "timeout");
}

async function loadChatHistory() {
    loadingHistory.value = true;
    try {
        const { data, error } = await GalaxyApi().GET("/api/chat/history", {
            params: {
                query: { limit: 50 },
            },
        });

        if (data && !error) {
            chatHistory.value = data as unknown as ChatHistoryItem[];
        }
    } catch (e) {
        console.error("Failed to load chat history:", e);
    } finally {
        loadingHistory.value = false;
    }
}

async function clearHistory() {
    if (!confirm("Are you sure you want to clear your chat history?")) {
        return;
    }

    try {
        const { data, error } = await GalaxyApi().DELETE("/api/chat/history");
        if (!error && data) {
            console.log("Clear history response:", data);
            chatHistory.value = [];
            // Also clear current chat if it was from history
            if (currentChatId.value) {
                startNewChat();
            }
        } else if (error) {
            console.error("Failed to clear history - API error:", error);
            alert("Failed to clear history. Please try again.");
        }
    } catch (e) {
        console.error("Failed to clear history - exception:", e);
        alert("Failed to clear history. Please try again.");
    }
}

async function loadPreviousChat(item: ChatHistoryItem) {
    pendingCollapsedMessages.length = 0;
    // Try to load the full conversation from the backend
    try {
        // @ts-ignore TODO: Add pydantic model later
        const { data } = await GalaxyApi().GET(`/api/chat/exchange/{exchange_id}/messages`, {
            params: {
                path: {
                    exchange_id: item.id,
                },
            },
        });

        // TODO: Define proper type for response, then we wouldn't need to define `fullConversation` here separately
        const fullConversation = data as any[] | undefined;

        if (fullConversation && fullConversation.length > 0) {
            // Clear and rebuild messages from full conversation
            messages.value = [];
            deliveredTaskIds.clear();
            pyodideTaskToMessage.clear();
            const taskIdToMessage: Record<string, Message> = {};
            const pendingExecResults: Record<string, any> = {};

            const assistantMessagesToReplay: Message[] = [];
            for (let index = 0; index < fullConversation.length; index += 1) {
                const msg = fullConversation[index];
                if (msg?.role === "execution_result") {
                    if (msg.task_id) {
                        deliveredTaskIds.add(String(msg.task_id));
                        const target = taskIdToMessage[String(msg.task_id)];
                        if (target) {
                            applyExecutionResultMetadata(target, msg);
                        } else {
                            pendingExecResults[String(msg.task_id)] = msg;
                        }
                    }
                    continue;
                }
                if (msg?.role !== "user" && msg?.role !== "assistant") {
                    // Defensive: ignore unexpected roles to avoid template/runtime errors.
                    continue;
                }
                const message: Message = {
                    id: `hist-${msg.role}-${item.id}-${index}`,
                    role: msg.role as "user" | "assistant",
                    content: typeof msg.content === "string" ? msg.content : String(msg.content ?? ""),
                    timestamp: msg.timestamp ? new Date(msg.timestamp) : new Date(),
                    feedback: null,
                };

                if (msg.role === "assistant") {
                    message.agentType = msg.agent_type;
                    message.confidence = msg.agent_response?.confidence || "medium";
                    message.feedback = msg.feedback === 1 ? "up" : msg.feedback === 0 ? "down" : null;

                    if (msg.agent_response) {
                        message.agentResponse = msg.agent_response;
                        message.suggestions = normaliseSuggestions(msg.agent_response.suggestions);
                        const metadata = (msg.agent_response as any)?.metadata as Record<string, unknown> | undefined;
                        const steps = metadata ? normaliseAnalysisSteps((metadata as any)?.analysis_steps) : [];
                        if (steps.length) {
                            message.analysisSteps = steps;
                        }
                        if (metadata) {
                            const artifactSource =
                                (metadata as any)?.artifacts ?? (metadata as any)?.execution?.artifacts;
                            const storedArtifacts = normaliseArtifactList(artifactSource);
                            updateMessageOutputsFromArtifacts(message, storedArtifacts);
                            const plots = normalisePathList((metadata as any)?.plots);
                            message.generatedPlots = plots.length ? plots : undefined;
                            const files = normalisePathList((metadata as any)?.files);
                            message.generatedFiles = files.length ? files : undefined;
                            const executedTask = (metadata as any)?.executed_task;
                            if (executedTask?.task_id) {
                                deliveredTaskIds.add(String(executedTask.task_id));
                                pyodideTaskToMessage.set(String(executedTask.task_id), message);
                                taskIdToMessage[String(executedTask.task_id)] = message;
                            }
                            const pendingTask = (metadata as any)?.pyodide_task;
                            if (pendingTask?.task_id) {
                                pyodideTaskToMessage.set(String(pendingTask.task_id), message);
                                taskIdToMessage[String(pendingTask.task_id)] = message;
                            }
                            const taskIdsToCheck = [executedTask?.task_id, pendingTask?.task_id].filter(
                                Boolean,
                            ) as string[];
                            taskIdsToCheck.forEach((taskId) => {
                                if (pendingExecResults[taskId]) {
                                    applyExecutionResultMetadata(message, pendingExecResults[taskId]);
                                    delete pendingExecResults[taskId];
                                }
                            });
                        }
                    }
                }

                if (msg.role === "assistant") {
                    applyCollapseState(message);
                    if (message.isCollapsible) {
                        pendingCollapsedMessages.push(message);
                        continue;
                    }
                    attachPendingCollapsedMessages(message);
                    assistantMessagesToReplay.push(message);
                }

                messages.value.push(message);
            }

            applyDatasetSelectionFromMessages(fullConversation);
            assistantMessagesToReplay.forEach((assistantMessage) => maybeRunPyodideForMessage(assistantMessage));
            if (pendingCollapsedMessages.length) {
                pendingCollapsedMessages.forEach((msg) => messages.value.push(msg));
                pendingCollapsedMessages.length = 0;
            }
        } else {
            // Fallback to single message if no full conversation available
            loadSingleMessageFallback(item);
        }

        currentChatId.value = item.id;
        showHistory.value = false;
        nextTick(() => scrollToBottom());
    } catch (error) {
        console.error("Error loading full conversation:", error);
        // Fallback to simple loading on error
        loadSingleMessageFallback(item);
    }
}

function loadSingleMessageFallback(item: ChatHistoryItem) {
    // Fallback method for loading just the first message pair
    const userMessage: Message = {
        id: `hist-user-${item.id}`,
        role: "user",
        content: typeof item.query === "string" ? item.query : String(item.query ?? ""),
        timestamp: new Date(item.timestamp),
        feedback: null,
    };

    const assistantMessage: Message = {
        id: `hist-assistant-${item.id}`,
        role: "assistant",
        content: typeof item.response === "string" ? item.response : String(item.response ?? ""),
        timestamp: new Date(item.timestamp),
        agentType: item.agent_type,
        confidence: item.agent_response?.confidence || "medium",
        feedback: item.feedback === 1 ? "up" : item.feedback === 0 ? "down" : null,
    };

    if (item.agent_response) {
        assistantMessage.agentResponse = item.agent_response;
        assistantMessage.suggestions = normaliseSuggestions(item.agent_response.suggestions);
        const metadata = (item.agent_response as any)?.metadata as Record<string, unknown> | undefined;
        const steps = metadata ? normaliseAnalysisSteps((metadata as any)?.analysis_steps) : [];
        if (steps.length) {
            assistantMessage.analysisSteps = steps;
        }
        if (metadata) {
            const artifactSource = (metadata as any)?.artifacts ?? (metadata as any)?.execution?.artifacts;
            const storedArtifacts = normaliseArtifactList(artifactSource);
            updateMessageOutputsFromArtifacts(assistantMessage, storedArtifacts);
            const plots = normalisePathList((metadata as any)?.plots);
            if (plots.length) {
                assistantMessage.generatedPlots = plots;
            }
            const files = normalisePathList((metadata as any)?.files);
            if (files.length) {
                assistantMessage.generatedFiles = files;
            }
            const executedTask = (metadata as any)?.executed_task;
            if (executedTask?.task_id) {
                deliveredTaskIds.add(String(executedTask.task_id));
                pyodideTaskToMessage.set(String(executedTask.task_id), assistantMessage);
            }
            const pendingTask = (metadata as any)?.pyodide_task;
            if (pendingTask?.task_id) {
                pyodideTaskToMessage.set(String(pendingTask.task_id), assistantMessage);
            }
        }
    }

    applyCollapseState(assistantMessage);
    messages.value = [userMessage, assistantMessage];
    currentChatId.value = item.id;
    showHistory.value = false;
    nextTick(() => scrollToBottom());

    maybeRunPyodideForMessage(assistantMessage);

    const metadataDatasets = (item.agent_response as any)?.metadata?.datasets_used;
    if (Array.isArray(metadataDatasets) && metadataDatasets.length > 0) {
        selectedDatasets.value = metadataDatasets.map(String);
    }
}

async function loadLatestChat() {
    try {
        const { data, error } = await GalaxyApi().GET("/api/chat/history", {
            params: {
                query: { limit: 1 },
            },
        });

        if (data && !error && data.length > 0) {
            const latestChat = data[0] as unknown as ChatHistoryItem;
            await loadPreviousChat(latestChat);
            hasLoadedInitialChat.value = true;
        }
    } catch (e) {
        console.error("Failed to load latest chat:", e);
    }
}

/** Type guard to check if a message has artifacts */
function hasArtifacts(message: Message): message is Message & { artifacts: UploadedArtifact[] } {
    return Boolean(message.artifacts && message.artifacts.length > 0);
}

function startNewChat() {
    pendingCollapsedMessages.length = 0;
    // Clear messages and reset to welcome message
    messages.value = [
        {
            id: generateId(),
            role: "assistant",
            content: "👋 Starting a new conversation! How can I help you today?",
            timestamp: new Date(),
            agentType: "router",
            confidence: "high",
            feedback: null,
            isSystemMessage: true,
        },
    ];
    Object.keys(pyodideExecutions).forEach((key) => delete pyodideExecutions[key]);
    currentChatId.value = null;
    deliveredTaskIds.clear();
    pyodideTaskToMessage.clear();
    selectedDatasets.value = [];
    query.value = "";
    errorMessage.value = "";
}

function toggleHistory() {
    showHistory.value = !showHistory.value;
    if (showHistory.value && chatHistory.value.length === 0) {
        loadChatHistory();
    }
}
</script>

<template>
    <div class="chatgxy-container">
        <div class="chatgxy-header">
            <Heading h2 :icon="faMagic" size="lg">
                <span>ChatGXY</span>
            </Heading>
            <div class="header-actions">
                <button class="btn btn-sm btn-outline-primary" title="Start New Chat" @click="startNewChat">
                    <FontAwesomeIcon :icon="faPlus" fixed-width />
                    New
                </button>
                <button
                    class="btn btn-sm"
                    :class="showHistory ? 'btn-primary' : 'btn-outline-primary'"
                    :title="showHistory ? 'Hide History' : 'Show History'"
                    @click="toggleHistory">
                    <FontAwesomeIcon :icon="faHistory" fixed-width />
                </button>
            </div>
        </div>

        <div class="chatgxy-body">
            <!-- History Sidebar -->
            <div v-if="showHistory" class="history-sidebar">
                <div class="history-header">
                    <h5>Chat History</h5>
                    <button class="btn btn-sm btn-link text-danger p-0" title="Clear History" @click="clearHistory">
                        <FontAwesomeIcon :icon="faTrash" />
                    </button>
                </div>

                <div v-if="loadingHistory" class="text-center p-3">
                    <LoadingSpan message="Loading history..." />
                </div>

                <div v-else-if="chatHistory.length === 0" class="text-muted p-3 text-center">No chat history yet</div>

                <div v-else class="history-list">
                    <div
                        v-for="item in chatHistory"
                        :key="item.id"
                        class="history-item"
                        role="button"
                        tabindex="0"
                        @keydown.enter="() => loadPreviousChat(item)"
                        @click="() => loadPreviousChat(item)">
                        <div class="history-query">{{ item.query }}</div>
                        <div class="history-meta">
                            <span class="history-agent">
                                <FontAwesomeIcon :icon="getAgentIcon(item.agent_type)" fixed-width />
                            </span>
                            <span class="history-time">
                                <FontAwesomeIcon :icon="faClock" class="mr-1" />
                                <UtcDate :date="item.timestamp" mode="elapsed" />
                            </span>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Main Chat Area -->
            <div ref="chatContainer" class="chat-messages flex-grow-1">
                <div class="mb-3">
                    <div class="pb-2">Select a dataset for this chat</div>
                    <DatasetSelector
                        v-if="datasetOptions.length"
                        id="dataset-select"
                        v-model="selectedDatasetsFormData"
                        :loading="loadingDatasets"
                        :options="formDataOptions"
                        user-defined-title="Created for ChatGXY"
                        workflow-run />
                    <div v-if="datasetError" class="text-danger small mt-2">{{ datasetError }}</div>
                </div>

                <div
                    v-for="message in messages"
                    :key="message.id"
                    :class="['notebook-cell', message.role === 'user' ? 'query-cell' : 'response-cell']">
                    <!-- Query cell (user input) -->
                    <template v-if="message.role === 'user'">
                        <div class="cell-label">
                            <FontAwesomeIcon :icon="faUser" fixed-width />
                            <span>Query</span>
                        </div>
                        <div class="cell-content">{{ message.content }}</div>
                    </template>

                    <!-- Response cell (assistant output) -->
                    <template v-else>
                        <div class="cell-label">
                            <FontAwesomeIcon :icon="getAgentIcon(message.agentType)" fixed-width />
                            <span>{{ getAgentLabel(message.agentType) }}</span>
                            <span
                                v-if="message.agentResponse?.metadata?.handoff_info"
                                class="routing-badge"
                                :title="'Routed by ' + message.agentResponse.metadata.handoff_info.source_agent">
                                <!-- Had title as :title="message.routingInfo.reasoning" for DA agent -->
                                via Router
                            </span>
                        </div>
                        <div class="cell-content">
                            <!-- eslint-disable-next-line vue/no-v-html -->
                            <div v-html="safeRenderMarkdown(message.content)" />

                            <div v-if="isAwaitingExecution(message)" class="alert alert-warning pyodide-hint mb-2">
                                ⚙️ Analysis still running… please keep this tab open; refreshing will restart the
                                execution.
                            </div>
                            <div
                                v-else-if="message.agentResponse?.metadata?.pyodide_status === 'timeout'"
                                class="alert alert-warning pyodide-hint mb-2">
                                ⚠️ Previous run timed out before the result was sent. Please ask again if you still need
                                this step to complete.
                            </div>

                            <div v-if="message.artifacts?.length" class="mt-2">
                                <details open class="artifacts-panel">
                                    <summary class="text-muted">
                                        Saved Artifacts ({{ message.artifacts.length }})
                                    </summary>
                                    <div class="artifact-grid">
                                        <div
                                            v-for="artifact in message.artifacts"
                                            :key="artifact.dataset_id || artifact.name"
                                            class="artifact-grid-item">
                                            <div class="artifact-name">
                                                <button
                                                    v-if="artifact.download_url"
                                                    class="btn btn-link btn-sm p-0"
                                                    type="button"
                                                    @click="downloadArtifact(artifact)">
                                                    {{ artifact.name || artifact.dataset_id }}
                                                </button>
                                                <span v-else>{{ artifact.name || artifact.dataset_id }}</span>
                                                <span v-if="artifact.size" class="text-muted ml-1">
                                                    ({{ formatSize(artifact.size) }})
                                                </span>
                                            </div>
                                            <div
                                                v-if="
                                                    artifact.mime_type &&
                                                    artifact.mime_type.startsWith('image/') &&
                                                    artifact.download_url
                                                "
                                                class="artifact-preview mt-2">
                                                <img
                                                    :src="artifact.download_url"
                                                    :alt="artifact.name || 'plot preview'"
                                                    class="plot-preview img-thumbnail" />
                                            </div>
                                        </div>
                                    </div>
                                </details>
                            </div>

                            <template v-if="isDataAnalysisMessage(message)">
                                <details v-if="hasIntermediateDetails(message)" class="intermediate-panel card mt-2">
                                    <summary class="text-muted">Intermediate steps</summary>
                                    <div class="card-body">
                                        <div
                                            v-if="message.agentResponse?.metadata?.executed_task?.code"
                                            class="executed-code">
                                            <details>
                                                <summary class="text-muted">Executed Python Code</summary>
                                                <pre>{{ message.agentResponse?.metadata?.executed_task?.code }}</pre>
                                            </details>
                                            <div v-if="message.agentResponse?.metadata?.stdout" class="mt-2">
                                                <details>
                                                    <summary class="text-muted">Execution Stdout</summary>
                                                    <pre>{{ message.agentResponse?.metadata?.stdout }}</pre>
                                                </details>
                                            </div>
                                            <div v-if="message.agentResponse?.metadata?.stderr" class="mt-2">
                                                <details>
                                                    <summary class="text-muted">Execution Stderr</summary>
                                                    <pre class="text-danger">
                                                            {{ message.agentResponse?.metadata?.stderr }}
                                                        </pre
                                                    >
                                                </details>
                                            </div>
                                        </div>
                                        <div v-if="message.analysisSteps?.length" class="analysis-steps card mt-2">
                                            <div
                                                v-for="(step, idx) in message.analysisSteps"
                                                :key="idx"
                                                class="analysis-step"
                                                :class="[
                                                    step.type,
                                                    step.status && step.status !== 'pending' ? step.status : '',
                                                ]">
                                                <div class="analysis-step-header">
                                                    <span class="step-label">
                                                        {{
                                                            step.type === "thought"
                                                                ? "Plan"
                                                                : step.type === "action"
                                                                  ? "Action"
                                                                  : step.type === "observation"
                                                                    ? "Observation"
                                                                    : "Conclusion"
                                                        }}
                                                    </span>
                                                    <span
                                                        v-if="
                                                            step.type === 'action' &&
                                                            step.status &&
                                                            step.status !== 'pending'
                                                        "
                                                        class="step-status"
                                                        :class="step.status">
                                                        {{ step.status }}
                                                    </span>
                                                    <span
                                                        v-else-if="
                                                            step.type === 'observation' && step.success !== undefined
                                                        "
                                                        class="step-status"
                                                        :class="step.success ? 'completed' : 'error'">
                                                        {{ step.success ? "success" : "error" }}
                                                    </span>
                                                </div>
                                                <div class="analysis-step-body">
                                                    <pre v-if="step.type === 'action'">{{ step.content }}</pre>
                                                    <div v-else-if="step.type === 'observation'">
                                                        <div v-if="step.stdout">
                                                            <small class="text-muted">stdout</small>
                                                            <pre>{{ step.stdout }}</pre>
                                                        </div>
                                                        <div v-if="step.stderr">
                                                            <small class="text-muted">stderr</small>
                                                            <pre class="text-danger">{{ step.stderr }}</pre>
                                                        </div>
                                                        <div v-if="!step.stdout && !step.stderr">
                                                            No textual output.
                                                        </div>
                                                    </div>
                                                    <div v-else>{{ step.content }}</div>
                                                    <div
                                                        v-if="step.type === 'action' && step.requirements?.length"
                                                        class="step-requirements">
                                                        <small class="text-muted">
                                                            requirements: {{ step.requirements.join(", ") }}
                                                        </small>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                        <div
                                            v-if="message.role === 'assistant' && shouldShowPyodideStatus(message)"
                                            class="pyodide-status card mt-2">
                                            <div class="card-body">
                                                <div
                                                    v-if="pyodideStateForMessage(message)?.status === 'initialising'"
                                                    class="text-muted">
                                                    Preparing browser environment…
                                                </div>
                                                <div
                                                    v-else-if="pyodideStateForMessage(message)?.status === 'installing'"
                                                    class="text-muted">
                                                    Installing Python packages…
                                                </div>
                                                <div
                                                    v-else-if="pyodideStateForMessage(message)?.status === 'fetching'"
                                                    class="text-muted">
                                                    Downloading datasets…
                                                </div>
                                                <div
                                                    v-else-if="pyodideStateForMessage(message)?.status === 'running'"
                                                    class="text-muted">
                                                    Running generated Python in the browser…
                                                </div>
                                                <div
                                                    v-else-if="pyodideStateForMessage(message)?.status === 'submitting'"
                                                    class="text-muted">
                                                    Sending results back to Galaxy…
                                                </div>
                                                <div
                                                    v-else-if="pyodideStateForMessage(message)?.status === 'completed'"
                                                    class="text-success">
                                                    Execution completed in your browser.
                                                </div>
                                                <div
                                                    v-else-if="pyodideStateForMessage(message)?.status === 'error'"
                                                    class="text-danger">
                                                    Execution failed{{
                                                        pyodideStateForMessage(message)?.errorMessage
                                                            ? ": " + pyodideStateForMessage(message)?.errorMessage
                                                            : ""
                                                    }}
                                                </div>

                                                <div v-if="pyodideStateForMessage(message)?.stdout" class="mt-2">
                                                    <h6 class="mb-1">Stdout</h6>
                                                    <pre class="pyodide-stream">
                                                            {{ pyodideStateForMessage(message)?.stdout }}
                                                        </pre
                                                    >
                                                </div>
                                                <div v-if="pyodideStateForMessage(message)?.stderr" class="mt-2">
                                                    <h6 class="mb-1 text-danger">Stderr</h6>
                                                    <pre class="pyodide-stream text-danger">
                                                            {{ pyodideStateForMessage(message)?.stderr }}
                                                        </pre
                                                    >
                                                </div>
                                                <div
                                                    v-if="pyodideStateForMessage(message)?.artifacts.length"
                                                    class="mt-2">
                                                    <h6 class="mb-1">Artifacts</h6>
                                                    <div class="artifact-grid">
                                                        <div
                                                            v-for="artifact in pyodideStateForMessage(message)
                                                                ?.artifacts"
                                                            :key="artifact.dataset_id || artifact.name"
                                                            class="artifact-grid-item">
                                                            <div class="artifact-name">
                                                                {{ artifact.name || artifact.dataset_id }}
                                                            </div>
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                        <div
                                            v-if="message.collapsedHistory && message.collapsedHistory.length"
                                            class="intermediate-history mt-3">
                                            <h6 class="mb-2">Earlier steps ({{ message.collapsedHistory.length }})</h6>
                                            <div
                                                v-for="historyMessage in message.collapsedHistory"
                                                :key="historyMessage.id"
                                                class="previous-step mb-3">
                                                <div class="text-muted mb-2">
                                                    {{ collapsedSummary(historyMessage) }}
                                                </div>
                                                <div class="message-content">
                                                    <!-- eslint-disable-next-line vue/no-v-html -->
                                                    <div v-html="safeRenderMarkdown(historyMessage.content)" />
                                                    <div v-if="hasArtifacts(historyMessage)" class="mt-2">
                                                        <details open class="artifacts-panel">
                                                            <summary class="text-muted">
                                                                Saved Artifacts ({{ historyMessage.artifacts.length }})
                                                            </summary>
                                                            <div class="artifact-grid">
                                                                <div
                                                                    v-for="artifact in historyMessage.artifacts"
                                                                    :key="artifact.dataset_id || artifact.name"
                                                                    class="artifact-grid-item">
                                                                    <div class="artifact-name">
                                                                        <button
                                                                            v-if="artifact.download_url"
                                                                            class="btn btn-link btn-sm p-0"
                                                                            type="button"
                                                                            @click="downloadArtifact(artifact)">
                                                                            {{ artifact.name || artifact.dataset_id }}
                                                                        </button>
                                                                        <span v-else>{{
                                                                            artifact.name || artifact.dataset_id
                                                                        }}</span>
                                                                        <span
                                                                            v-if="artifact.size"
                                                                            class="text-muted ml-1">
                                                                            ({{ formatSize(artifact.size) }})
                                                                        </span>
                                                                    </div>
                                                                    <div
                                                                        v-if="
                                                                            artifact.mime_type &&
                                                                            artifact.mime_type.startsWith('image/') &&
                                                                            artifact.download_url
                                                                        "
                                                                        class="artifact-preview mt-2">
                                                                        <img
                                                                            :src="artifact.download_url"
                                                                            :alt="artifact.name || 'plot preview'"
                                                                            class="plot-preview img-thumbnail" />
                                                                    </div>
                                                                </div>
                                                            </div>
                                                        </details>
                                                    </div>
                                                    <div
                                                        v-if="
                                                            historyMessage.agentResponse?.metadata?.executed_task?.code
                                                        "
                                                        class="mt-2 executed-code">
                                                        <details open>
                                                            <summary class="text-muted">Executed Python Code</summary>
                                                            <pre>{{
                                                                historyMessage.agentResponse?.metadata?.executed_task
                                                                    ?.code
                                                            }}</pre>
                                                        </details>
                                                        <div
                                                            v-if="historyMessage.agentResponse?.metadata?.stdout"
                                                            class="mt-2">
                                                            <details open>
                                                                <summary class="text-muted">Execution Stdout</summary>
                                                                <pre>{{
                                                                    historyMessage.agentResponse?.metadata?.stdout
                                                                }}</pre>
                                                            </details>
                                                        </div>
                                                        <div
                                                            v-if="historyMessage.agentResponse?.metadata?.stderr"
                                                            class="mt-2">
                                                            <details>
                                                                <summary class="text-muted">Execution Stderr</summary>
                                                                <pre class="text-danger">{{
                                                                    historyMessage.agentResponse?.metadata?.stderr
                                                                }}</pre>
                                                            </details>
                                                        </div>
                                                    </div>
                                                </div>
                                                <div
                                                    v-if="historyMessage.analysisSteps?.length"
                                                    class="analysis-steps card mt-2">
                                                    <div
                                                        v-for="(step, idx) in historyMessage.analysisSteps"
                                                        :key="idx"
                                                        class="analysis-step"
                                                        :class="[
                                                            step.type,
                                                            step.status && step.status !== 'pending' ? step.status : '',
                                                        ]">
                                                        <div class="analysis-step-header">
                                                            <span class="step-label">
                                                                {{
                                                                    step.type === "thought"
                                                                        ? "Plan"
                                                                        : step.type === "action"
                                                                          ? "Action"
                                                                          : step.type === "observation"
                                                                            ? "Observation"
                                                                            : "Conclusion"
                                                                }}
                                                            </span>
                                                            <span
                                                                v-if="
                                                                    step.type === 'action' &&
                                                                    step.status &&
                                                                    step.status !== 'pending'
                                                                "
                                                                class="step-status"
                                                                :class="step.status">
                                                                {{ step.status }}
                                                            </span>
                                                            <span
                                                                v-else-if="
                                                                    step.type === 'observation' &&
                                                                    step.success !== undefined
                                                                "
                                                                class="step-status"
                                                                :class="step.success ? 'completed' : 'error'">
                                                                {{ step.success ? "success" : "error" }}
                                                            </span>
                                                        </div>
                                                        <div class="analysis-step-body">
                                                            <pre v-if="step.type === 'action'">{{ step.content }}</pre>
                                                            <div v-else-if="step.type === 'observation'">
                                                                <div v-if="step.stdout">
                                                                    <small class="text-muted">stdout</small>
                                                                    <pre>{{ step.stdout }}</pre>
                                                                </div>
                                                                <div v-if="step.stderr">
                                                                    <small class="text-muted">stderr</small>
                                                                    <pre class="text-danger">{{ step.stderr }}</pre>
                                                                </div>
                                                                <div v-if="!step.stdout && !step.stderr">
                                                                    No textual output.
                                                                </div>
                                                            </div>
                                                            <div v-else>{{ step.content }}</div>
                                                            <div
                                                                v-if="
                                                                    step.type === 'action' && step.requirements?.length
                                                                "
                                                                class="step-requirements">
                                                                <small class="text-muted">
                                                                    requirements:
                                                                    {{ step.requirements.join(", ") }}
                                                                </small>
                                                            </div>
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </details>
                            </template>

                            <div v-if="message.agentResponse?.metadata?.executed_task?.code" class="mt-2 executed-code">
                                <details open>
                                    <summary class="text-muted">Executed Python Code</summary>
                                    <pre>{{ message.agentResponse?.metadata?.executed_task?.code }}</pre>
                                </details>
                                <div v-if="message.agentResponse?.metadata?.stdout" class="mt-2">
                                    <details open>
                                        <summary class="text-muted">Execution Stdout</summary>
                                        <pre>{{ message.agentResponse?.metadata?.stdout }}</pre>
                                    </details>
                                </div>
                                <div v-if="message.agentResponse?.metadata?.stderr" class="mt-2">
                                    <details>
                                        <summary class="text-muted">Execution Stderr</summary>
                                        <pre class="text-danger">{{ message.agentResponse?.metadata?.stderr }}</pre>
                                    </details>
                                </div>
                            </div>

                            <div v-if="message.analysisSteps?.length" class="analysis-steps card mt-2">
                                <div
                                    v-for="(step, idx) in message.analysisSteps"
                                    :key="idx"
                                    class="analysis-step"
                                    :class="[step.type, step.status && step.status !== 'pending' ? step.status : '']">
                                    <div class="analysis-step-header">
                                        <span class="step-label">
                                            {{
                                                step.type === "thought"
                                                    ? "Plan"
                                                    : step.type === "action"
                                                      ? "Action"
                                                      : step.type === "observation"
                                                        ? "Observation"
                                                        : "Conclusion"
                                            }}
                                        </span>
                                        <span
                                            v-if="step.type === 'action' && step.status && step.status !== 'pending'"
                                            class="step-status"
                                            :class="step.status">
                                            {{ step.status }}
                                        </span>
                                        <span
                                            v-else-if="step.type === 'observation' && step.success !== undefined"
                                            class="step-status"
                                            :class="step.success ? 'completed' : 'error'">
                                            {{ step.success ? "success" : "error" }}
                                        </span>
                                    </div>
                                    <div class="analysis-step-body">
                                        <pre v-if="step.type === 'action'">{{ step.content }}</pre>
                                        <div v-else-if="step.type === 'observation'">
                                            <div v-if="step.stdout">
                                                <small class="text-muted">stdout</small>
                                                <pre>{{ step.stdout }}</pre>
                                            </div>
                                            <div v-if="step.stderr">
                                                <small class="text-muted">stderr</small>
                                                <pre class="text-danger">{{ step.stderr }}</pre>
                                            </div>
                                            <div v-if="!step.stdout && !step.stderr">No textual output.</div>
                                        </div>
                                        <div v-else>{{ step.content }}</div>
                                        <div
                                            v-if="step.type === 'action' && step.requirements?.length"
                                            class="step-requirements">
                                            <small class="text-muted">
                                                requirements: {{ step.requirements.join(", ") }}
                                            </small>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <div v-if="shouldShowPyodideStatus(message)" class="pyodide-status card mt-2">
                                <div class="card-body">
                                    <div
                                        v-if="pyodideStateForMessage(message)?.status === 'initialising'"
                                        class="text-muted">
                                        Preparing browser environment…
                                    </div>
                                    <div
                                        v-else-if="pyodideStateForMessage(message)?.status === 'installing'"
                                        class="text-muted">
                                        Installing Python packages…
                                    </div>
                                    <div
                                        v-else-if="pyodideStateForMessage(message)?.status === 'fetching'"
                                        class="text-muted">
                                        Downloading datasets…
                                    </div>
                                    <div
                                        v-else-if="pyodideStateForMessage(message)?.status === 'running'"
                                        class="text-muted">
                                        Running generated Python in the browser…
                                    </div>
                                    <div
                                        v-else-if="pyodideStateForMessage(message)?.status === 'submitting'"
                                        class="text-muted">
                                        Sending results back to Galaxy…
                                    </div>
                                    <div
                                        v-else-if="pyodideStateForMessage(message)?.status === 'completed'"
                                        class="text-success">
                                        Execution completed in your browser.
                                    </div>
                                    <div
                                        v-else-if="pyodideStateForMessage(message)?.status === 'error'"
                                        class="text-danger">
                                        Execution failed{{
                                            pyodideStateForMessage(message)?.errorMessage
                                                ? ": " + pyodideStateForMessage(message)?.errorMessage
                                                : ""
                                        }}
                                    </div>

                                    <div v-if="pyodideStateForMessage(message)?.stdout" class="mt-2">
                                        <h6 class="mb-1">Stdout</h6>
                                        <pre class="pyodide-stream">{{ pyodideStateForMessage(message)?.stdout }}</pre>
                                    </div>
                                    <div v-if="pyodideStateForMessage(message)?.stderr" class="mt-2">
                                        <h6 class="mb-1 text-danger">Stderr</h6>
                                        <pre class="pyodide-stream text-danger">
                                                {{ pyodideStateForMessage(message)?.stderr }}
                                            </pre
                                        >
                                    </div>
                                    <div v-if="pyodideStateForMessage(message)?.artifacts.length" class="mt-2">
                                        <h6 class="mb-1">Artifacts</h6>
                                        <div class="artifact-grid">
                                            <div
                                                v-for="artifact in pyodideStateForMessage(message)?.artifacts"
                                                :key="artifact.dataset_id || artifact.name"
                                                class="artifact-grid-item">
                                                <div class="artifact-name">
                                                    {{ artifact.name || artifact.dataset_id }}
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <div
                                v-if="
                                    !isDataAnalysisMessage(message) &&
                                    message.collapsedHistory &&
                                    message.collapsedHistory.length
                                "
                                class="collapsed-history mt-3">
                                <details
                                    class="intermediate-details"
                                    :open="!message.isCollapsed"
                                    @toggle="handleIntermediateToggle($event, message)">
                                    <summary>
                                        <span>Intermediate steps ({{ message.collapsedHistory.length }})</span>
                                        <span class="chip-chevron" :class="{ open: !message.isCollapsed }">›</span>
                                    </summary>
                                    <div class="collapsed-entry-body card card-body mt-3">
                                        <div
                                            v-for="historyMessage in message.collapsedHistory"
                                            :key="historyMessage.id"
                                            class="previous-step mb-4">
                                            <div class="text-muted mb-2">
                                                {{ collapsedSummary(historyMessage) }}
                                            </div>
                                            <div class="message-content">
                                                <!-- eslint-disable-next-line vue/no-v-html -->
                                                <div v-html="safeRenderMarkdown(historyMessage.content)" />
                                                <div v-if="hasArtifacts(historyMessage)" class="mt-2">
                                                    <details open class="artifacts-panel">
                                                        <summary class="text-muted">
                                                            Saved Artifacts ({{ historyMessage.artifacts.length }})
                                                        </summary>
                                                        <div class="artifact-grid">
                                                            <div
                                                                v-for="artifact in historyMessage.artifacts"
                                                                :key="artifact.dataset_id || artifact.name"
                                                                class="artifact-grid-item">
                                                                <div class="artifact-name">
                                                                    <button
                                                                        v-if="artifact.download_url"
                                                                        class="btn btn-link btn-sm p-0"
                                                                        type="button"
                                                                        @click="downloadArtifact(artifact)">
                                                                        {{ artifact.name || artifact.dataset_id }}
                                                                    </button>
                                                                    <span v-else>{{
                                                                        artifact.name || artifact.dataset_id
                                                                    }}</span>
                                                                    <span v-if="artifact.size" class="text-muted ml-1">
                                                                        ({{ formatSize(artifact.size) }})
                                                                    </span>
                                                                </div>
                                                                <div
                                                                    v-if="
                                                                        artifact.mime_type &&
                                                                        artifact.mime_type.startsWith('image/') &&
                                                                        artifact.download_url
                                                                    "
                                                                    class="artifact-preview mt-2">
                                                                    <img
                                                                        :src="artifact.download_url"
                                                                        :alt="artifact.name || 'plot preview'"
                                                                        class="plot-preview img-thumbnail" />
                                                                </div>
                                                            </div>
                                                        </div>
                                                    </details>
                                                </div>
                                                <div
                                                    v-if="historyMessage.agentResponse?.metadata?.executed_task?.code"
                                                    class="mt-2 executed-code">
                                                    <details open>
                                                        <summary class="text-muted">Executed Python Code</summary>
                                                        <pre>
                                                                {{
                                                                historyMessage.agentResponse?.metadata?.executed_task
                                                                    ?.code
                                                            }}
                                                            </pre
                                                        >
                                                    </details>
                                                    <div
                                                        v-if="historyMessage.agentResponse?.metadata?.stdout"
                                                        class="mt-2">
                                                        <details open>
                                                            <summary class="text-muted">Execution Stdout</summary>
                                                            <pre>
                                                                    {{ historyMessage.agentResponse?.metadata?.stdout }}
                                                                </pre
                                                            >
                                                        </details>
                                                    </div>
                                                    <div
                                                        v-if="historyMessage.agentResponse?.metadata?.stderr"
                                                        class="mt-2">
                                                        <details>
                                                            <summary class="text-muted">Execution Stderr</summary>
                                                            <pre class="text-danger">
                                                                    {{ historyMessage.agentResponse?.metadata?.stderr }}
                                                                </pre
                                                            >
                                                        </details>
                                                    </div>
                                                </div>
                                            </div>
                                            <div
                                                v-if="historyMessage.analysisSteps?.length"
                                                class="analysis-steps card mt-2">
                                                <div
                                                    v-for="(step, idx) in historyMessage.analysisSteps"
                                                    :key="idx"
                                                    class="analysis-step"
                                                    :class="[
                                                        step.type,
                                                        step.status && step.status !== 'pending' ? step.status : '',
                                                    ]">
                                                    <div class="analysis-step-header">
                                                        <span class="step-label">
                                                            {{
                                                                step.type === "thought"
                                                                    ? "Plan"
                                                                    : step.type === "action"
                                                                      ? "Action"
                                                                      : step.type === "observation"
                                                                        ? "Observation"
                                                                        : "Conclusion"
                                                            }}
                                                        </span>
                                                        <span
                                                            v-if="
                                                                step.type === 'action' &&
                                                                step.status &&
                                                                step.status !== 'pending'
                                                            "
                                                            class="step-status"
                                                            :class="step.status">
                                                            {{ step.status }}
                                                        </span>
                                                        <span
                                                            v-else-if="
                                                                step.type === 'observation' &&
                                                                step.success !== undefined
                                                            "
                                                            class="step-status"
                                                            :class="step.success ? 'completed' : 'error'">
                                                            {{ step.success ? "success" : "error" }}
                                                        </span>
                                                    </div>
                                                    <div class="analysis-step-body">
                                                        <pre v-if="step.type === 'action'">{{ step.content }}</pre>
                                                        <div v-else-if="step.type === 'observation'">
                                                            <div v-if="step.stdout">
                                                                <small class="text-muted">stdout</small>
                                                                <pre>{{ step.stdout }}</pre>
                                                            </div>
                                                            <div v-if="step.stderr">
                                                                <small class="text-muted">stderr</small>
                                                                <pre class="text-danger">{{ step.stderr }}</pre>
                                                            </div>
                                                            <div v-if="!step.stdout && !step.stderr">
                                                                No textual output.
                                                            </div>
                                                        </div>
                                                        <div v-else>{{ step.content }}</div>
                                                        <div
                                                            v-if="step.type === 'action' && step.requirements?.length"
                                                            class="step-requirements">
                                                            <small class="text-muted">
                                                                requirements: {{ step.requirements.join(", ") }}
                                                            </small>
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </details>
                            </div>

                            <!-- Action suggestions -->
                            <ActionCard
                                v-if="Array.isArray(message.suggestions) && message.suggestions.length"
                                :suggestions="message.suggestions"
                                :processing-action="processingAction"
                                @handle-action="
                                    (action) => handleAction(action, getAgentResponseOrEmpty(message.agentResponse))
                                " />
                        </div>
                        <div
                            v-if="!(message.content || '').startsWith('❌') && !message.isSystemMessage"
                            class="cell-footer">
                            <div class="feedback-actions">
                                <button
                                    class="feedback-btn"
                                    :disabled="message.feedback !== null"
                                    :class="{ active: message.feedback === 'up' }"
                                    title="Helpful"
                                    @click="sendFeedback(message.id, 'up')">
                                    <FontAwesomeIcon :icon="faThumbsUp" fixed-width />
                                </button>
                                <button
                                    class="feedback-btn"
                                    :disabled="message.feedback !== null"
                                    :class="{ active: message.feedback === 'down' }"
                                    title="Not helpful"
                                    @click="sendFeedback(message.id, 'down')">
                                    <FontAwesomeIcon :icon="faThumbsDown" fixed-width />
                                </button>
                                <span v-if="message.feedback" class="feedback-text">Thanks!</span>
                            </div>
                            <div class="response-stats">
                                <span class="stat-item" :title="'Agent: ' + getAgentLabel(message.agentType)">
                                    <FontAwesomeIcon :icon="getAgentIcon(message.agentType)" fixed-width />
                                    {{ getAgentLabel(message.agentType) }}
                                </span>
                                <span
                                    v-if="message.agentResponse?.metadata?.model"
                                    class="stat-item"
                                    :title="'Model: ' + message.agentResponse.metadata.model">
                                    {{ formatModelName(message.agentResponse.metadata.model) }}
                                </span>
                                <span
                                    v-if="message.agentResponse?.metadata?.total_tokens"
                                    class="stat-item"
                                    title="Tokens used">
                                    {{ message.agentResponse.metadata.total_tokens }} tokens
                                </span>
                            </div>
                        </div>
                    </template>
                </div>

                <!-- Loading state -->
                <div v-if="busy" class="notebook-cell response-cell loading-cell">
                    <div class="cell-label">
                        <FontAwesomeIcon :icon="getAgentIcon(selectedAgentType)" fixed-width />
                        <span>{{ getAgentLabel(selectedAgentType) }}</span>
                    </div>
                    <div class="cell-content">
                        <BSkeleton animation="wave" width="85%" />
                        <BSkeleton animation="wave" width="55%" />
                        <BSkeleton animation="wave" width="70%" />
                    </div>
                </div>
            </div>
        </div>

        <div class="chatgxy-footer">
            <div class="chat-input-container">
                <label for="chat-input" class="sr-only">Chat message</label>
                <textarea
                    id="chat-input"
                    v-model="query"
                    :disabled="isChatBusy"
                    placeholder="Ask about tools, workflows, errors, or anything Galaxy..."
                    rows="1"
                    class="form-control chat-input"
                    @keydown.enter.prevent="!$event.shiftKey && submitQuery()" />
                <button :disabled="busy || !query.trim()" class="btn btn-primary send-button" @click="submitQuery">
                    <FontAwesomeIcon v-if="!busy" :icon="faPaperPlane" fixed-width />
                    <LoadingSpan v-else message="" />
                </button>
            </div>
        </div>
    </div>
</template>

<style lang="scss" scoped>
@import "@/style/scss/theme/blue.scss";

.chatgxy-container {
    height: calc(100vh - #{$masthead-height} - 2rem);
    display: flex;
    flex-direction: column;
    background: $white;
    border-radius: $border-radius-large;
    overflow: hidden;
}

.chatgxy-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.75rem 1rem;
    background: $panel-bg-color;
    border-bottom: $border-default;

    .header-actions {
        display: flex;
        gap: 0.5rem;
    }
}

.chatgxy-body {
    flex: 1;
    display: flex;
    overflow: hidden;
}

.chatgxy-footer {
    padding: 0.75rem 1rem;
    background: $panel-bg-color;
    border-top: $border-default;
}

// Notebook-style cells
.chat-messages {
    flex: 1;
    overflow-y: auto;
    padding: 1rem 1.5rem;
    background: $white;
}

.analysis-steps {
    border: 1px solid #dee2e6;
    border-radius: 6px;
    padding: 0.75rem;
    background: white;
}

.analysis-step + .analysis-step {
    margin-top: 0.75rem;
}

.analysis-step-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-weight: 600;
    font-size: 0.9rem;
}

.analysis-step-header .step-label {
    text-transform: capitalize;
}

.analysis-step-header .step-status {
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    padding: 0.1rem 0.4rem;
    border-radius: 9999px;
    margin-left: 0.5rem;
}

.analysis-step.running .step-status {
    background: #fff3cd;
    color: #856404;
}

.analysis-step.completed .step-status {
    background: #d4edda;
    color: #155724;
}

.analysis-step.error .step-status {
    background: #f8d7da;
    color: #721c24;
}

.analysis-step-body {
    margin-top: 0.5rem;
    font-size: 0.9rem;
}

.analysis-step-body pre {
    background: #f1f3f5;
    color: #212529;
    padding: 0.5rem;
    border-radius: 4px;
    white-space: pre-wrap;
    border: 1px solid #d1d5db;
}

.analysis-step-body .text-danger {
    color: #dc3545 !important;
}

.collapsed-history {
    details {
        border: 1px solid #dfe3e6;
        border-radius: 8px;
        background: #f7f8fa;
        padding: 0.25rem 0.75rem;
    }

    summary {
        display: flex;
        align-items: center;
        justify-content: space-between;
        font-size: 0.85rem;
        font-weight: 600;
        color: #1f2a37;
        list-style: none;
        cursor: pointer;
        padding: 0.25rem 0;
    }

    summary::-webkit-details-marker {
        display: none;
    }

    .chip-chevron {
        margin-left: 0.75rem;
        transition: transform 0.2s ease;

        &.open {
            transform: rotate(90deg);
        }
    }

    .collapsed-entry-body {
        background: #fff;
    }
}

.pyodide-status {
    border: 1px dashed #6c757d;
    background: #f8f9fa;
}

.pyodide-hint {
    font-size: 0.85rem;
}

.pyodide-status .pyodide-stream {
    background: #1e1e1e;
    color: #f8f9fa;
    padding: 0.5rem;
    border-radius: 4px;
    max-height: 200px;
    overflow: auto;
    font-family: var(--font-family-monospace);
    font-size: 0.85rem;
}

.pyodide-status .pyodide-stream.text-danger {
    color: #f8d7da;
}

.plot-preview {
    max-width: 320px;
    border: 1px solid #dee2e6;
    border-radius: 4px;
    background: #fff;
    width: 100%;
}

.artifacts-panel summary {
    cursor: pointer;
    font-weight: 600;
}

.intermediate-panel {
    summary {
        cursor: pointer;
        font-weight: 600;
    }
}

.artifact-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 0.5rem;
}

.artifact-grid-item {
    border: 1px solid #edf0f3;
    border-radius: 6px;
    padding: 0.5rem;
    background: #fbfbfd;
    min-height: 120px;
}

.artifact-grid-item .artifact-name {
    font-size: 0.9rem;
    margin-bottom: 0.25rem;
}

.artifact-grid-item .artifact-name > .btn-link,
.artifact-grid-item .artifact-name > span:not(.text-muted) {
    display: block;
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.artifact-grid-item .artifact-name > span.text-muted {
    display: block;
}

.artifact-preview img {
    max-height: 180px;
    object-fit: contain;
}

.step-requirements {
    margin-top: 0.35rem;
    font-size: 0.75rem;
}

.notebook-cell {
    margin-bottom: 1rem;
    animation: fadeIn 0.2s ease-out;

    &.query-cell {
        .cell-label {
            color: $brand-primary;
        }

        .cell-content {
            border-left: 3px solid $brand-primary;
            background: rgba($brand-primary, 0.04);
            padding: 0.75rem 1rem;
            font-size: 0.95rem;
            color: $text-color;
        }
    }

    &.response-cell {
        .cell-label {
            color: $text-muted;
        }

        .cell-content {
            border-left: 3px solid $brand-secondary;
            background: $panel-bg-color;
            padding: 0.75rem 1rem;
        }

        &.loading-cell {
            .cell-content {
                opacity: 0.7;
            }
        }
    }
}

.cell-label {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.025em;
    margin-bottom: 0.375rem;
    padding-left: 0.25rem;
}

.routing-badge {
    font-weight: 400;
    font-size: 0.65rem;
    color: $text-light;
    text-transform: none;
    cursor: help;

    &::before {
        content: "·";
        margin: 0 0.25rem;
    }
}

.cell-content {
    border-radius: $border-radius-base;
    word-wrap: break-word;
    line-height: 1.6;

    :deep(p:last-child) {
        margin-bottom: 0;
    }

    :deep(p:first-child) {
        margin-top: 0;
    }

    :deep(code) {
        background: rgba($brand-dark, 0.08);
        padding: 0.125rem 0.375rem;
        border-radius: $border-radius-base;
        font-family: $font-family-monospace;
        font-size: 0.85em;
    }

    :deep(pre) {
        background: $white;
        border: $border-default;
        padding: 0.75rem;
        border-radius: $border-radius-base;
        overflow-x: auto;
        margin: 0.75rem 0;

        code {
            background: none;
            padding: 0;
        }
    }

    :deep(ul),
    :deep(ol) {
        margin-bottom: 0.75rem;
        padding-left: 1.5rem;
    }

    :deep(li) {
        margin-bottom: 0.25rem;
    }
}

.cell-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-top: 0.5rem;
    padding-left: 0.25rem;
}

.feedback-actions {
    display: flex;
    align-items: center;
    gap: 0.25rem;
}

.response-stats {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    font-size: 0.7rem;
    color: $text-light;

    .stat-item {
        display: flex;
        align-items: center;
        gap: 0.25rem;
    }
}

.feedback-btn {
    background: none;
    border: none;
    padding: 0.25rem 0.5rem;
    color: $text-light;
    cursor: pointer;
    border-radius: $border-radius-base;
    transition: all 0.15s;

    &:hover:not(:disabled) {
        color: $brand-primary;
        background: rgba($brand-primary, 0.08);
    }

    &:disabled {
        cursor: default;
        opacity: 0.5;
    }

    &.active {
        color: $brand-success;
    }
}

.feedback-text {
    font-size: 0.7rem;
    color: $text-light;
    margin-left: 0.25rem;
}

// Input area
.chat-input-container {
    display: flex;
    gap: 0.5rem;
    align-items: flex-end;

    .chat-input {
        flex: 1;
        resize: none;
        border-radius: $border-radius-base;
        padding: 0.625rem 0.875rem;
        border: $border-default;
        font-size: 0.9rem;
        min-height: 2.5rem;
        max-height: 8rem;

        &:focus {
            border-color: $brand-primary;
            box-shadow: 0 0 0 2px rgba($brand-primary, 0.1);
            outline: none;
        }
    }

    .send-button {
        flex-shrink: 0;
        border-radius: $border-radius-base;
        padding: 0.5rem 0.875rem;
    }
}

// History sidebar
.history-sidebar {
    width: 280px;
    border-right: $border-default;
    background: $panel-bg-color;
    display: flex;
    flex-direction: column;

    .history-header {
        padding: 0.75rem 1rem;
        border-bottom: $border-default;
        display: flex;
        justify-content: space-between;
        align-items: center;

        h5 {
            margin: 0;
            font-size: 0.875rem;
            font-weight: 600;
            color: $text-color;
        }
    }

    .history-list {
        flex: 1;
        overflow-y: auto;
    }

    .history-item {
        padding: 0.625rem 1rem;
        border-bottom: 1px solid darken($panel-bg-color, 5%);
        cursor: pointer;
        transition: background-color 0.15s;

        &:hover {
            background: darken($panel-bg-color, 3%);
        }

        .history-query {
            font-size: 0.8rem;
            color: $text-color;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            margin-bottom: 0.25rem;
        }

        .history-meta {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.7rem;
            color: $text-light;

            .history-agent {
                color: $brand-primary;
            }

            .history-time {
                display: flex;
                align-items: center;
                gap: 0.25rem;
            }
        }
    }
}

// Animations
@keyframes fadeIn {
    from {
        opacity: 0;
        transform: translateY(4px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

// Accessibility
.sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
}
</style>
