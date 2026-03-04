<script setup lang="ts">
import {
    faClock,
    faExternalLinkAlt,
    faHistory,
    faMagic,
    faMicroscope,
    faPlus,
    faTrash,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BSkeleton } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";

import { GalaxyApi } from "@/api";
import { getGalaxyInstance } from "@/app";
import { useAgentActions } from "@/composables/agentActions";
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

import { getAgentIcon } from "./ChatGXY/agentTypes";
import type { ChatMessage } from "./ChatGXY/chatTypes";
import { generateId, scrollToBottom } from "./ChatGXY/chatUtils";
import type {
    AnalysisStep,
    ChatHistoryItem,
    ConfidenceLevel,
    ExecutionState,
    Message,
    UploadedArtifact,
} from "./ChatGXY/types";
import { hasArtifacts } from "./ChatGXY/utilities";
import type { DataOption } from "./Form/Elements/FormData/types";

import GButton from "./BaseComponents/GButton.vue";
import ChatInput from "./ChatGXY/ChatInput.vue";
import ChatMessageCell from "./ChatGXY/ChatMessageCell.vue";
import MessageArtifacts from "./ChatGXY/MessageArtifacts.vue";
import MessageIntermediateDetails from "./ChatGXY/MessageIntermediateDetails.vue";
import DatasetSelector from "./Form/Elements/FormData/FormData.vue";
import Heading from "@/components/Common/Heading.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import UtcDate from "@/components/UtcDate.vue";

const props = withDefaults(
    defineProps<{
        exchangeId?: string;
        compact?: boolean;
    }>(),
    {
        exchangeId: undefined,
        compact: false,
    },
);

const query = ref("");
const messages = ref<ChatMessage[]>([]);
const busy = ref(false);
const chatContainer = ref<HTMLElement>();
const selectedAgentType = ref("auto");
const currentChatId = ref<number | null>(null);
const hasLoadedInitialChat = ref(false);
const pendingCollapsedMessages: Message[] = [];

// ── History sidebar state ─────────────────────────────────────────────────────
const showHistory = ref(false);
const chatHistory = ref<ChatHistoryItem[]>([]);
const loadingHistory = ref(false);

// ── Dataset selection state ───────────────────────────────────────────────────
const selectedDatasets = ref<string[]>([]);
/** Whether fetching datasets is allowed/enabled (for Data Analysis agent type) */
const allowFetchingDatasets = ref(false);

const { currentHistoryId } = storeToRefs(useHistoryStore());

const {
    datasets: currentHistoryDatasets,
    isFetching: loadingDatasets,
    error: datasetError,
} = useHistoryDatasets({
    historyId: () => currentHistoryId.value || "",
    enabled: () => currentHistoryId.value !== null && allowFetchingDatasets.value,
});

const datasetOptions = computed<DataOption[]>(() => {
    if (loadingDatasets.value) {
        return [];
    }
    return currentHistoryDatasets.value
        .map((item) => {
            const name = item.name || `Dataset ${item.hid || ""}`;
            const hidden = Boolean(item.visible === false);
            const generated = typeof name === "string" && name.trim().toLowerCase().startsWith("generated_file");
            if (!item.id || hidden || generated) {
                return null;
            }
            return { id: item.id, hid: item.hid, name, src: "hda" } as DataOption;
        })
        .filter((entry): entry is DataOption => entry !== null && Boolean(entry));
});

const selectedDatasetsFormData = computed<{ values: Array<DataOption> } | null>({
    get() {
        if (selectedDatasets.value.length === 0) {
            return null;
        }
        const selected = datasetOptions.value.filter((dataset) => selectedDatasets.value.includes(dataset.id));
        return { values: selected };
    },
    set(value) {
        if (value === null) {
            selectedDatasets.value = [];
        } else {
            selectedDatasets.value = value.values.map((dataset) => dataset.id);
        }
    },
});

const formDataOptions = computed<Record<string, Array<DataOption>>>(() => ({ hda: datasetOptions.value }));

watch(
    () => datasetOptions.value,
    () => {
        const validIds = new Set(datasetOptions.value.map((entry) => entry.id));
        selectedDatasets.value = selectedDatasets.value.filter((id) => validIds.has(id));
    },
    { immediate: true, deep: true },
);

watch(
    () => currentHistoryId.value,
    () => {
        selectedDatasets.value = [];
    },
    { immediate: false },
);

// ── Pyodide / streaming state ─────────────────────────────────────────────────
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

// ── Composables ───────────────────────────────────────────────────────────────
const { renderMarkdown } = useMarkdown({ openLinksInNewPage: true, removeNewlinesAfterList: true });
const { processingAction, handleAction } = useAgentActions();

// ── Lifecycle ─────────────────────────────────────────────────────────────────
onMounted(async () => {
    if (props.exchangeId) {
        await loadChatById(props.exchangeId);
    } else {
        await loadLatestChat();
    }
    if (!hasLoadedInitialChat.value) {
        showWelcome();
    }
});

onBeforeUnmount(() => {
    closeChatStream();
});

// ── Watchers ──────────────────────────────────────────────────────────────────
watch(
    () => props.exchangeId,
    async (newId, oldId) => {
        if (newId === oldId) {
            return;
        }
        if (newId) {
            await loadChatById(newId);
        } else {
            startNewChat();
        }
    },
);

watch(busy, (isBusy) => {
    if (isBusy) {
        nextTick(() => scrollToBottom(chatContainer.value));
    }
});

watch(
    messages,
    () => {
        ensurePendingPyodideTasks();
    },
    { deep: true },
);

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

// ── Helpers ───────────────────────────────────────────────────────────────────
function escapeHtml(raw: string): string {
    return raw
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

function safeRenderMarkdown(text: string): string {
    try {
        return renderMarkdown(text);
    } catch (error) {
        console.error("Failed to render markdown for chat message:", error);
        return `<pre>${escapeHtml(text)}</pre>`;
    }
}

function normaliseSuggestions(raw: unknown) {
    return Array.isArray(raw) ? raw : [];
}

// ── Chat state management ─────────────────────────────────────────────────────
function showWelcome() {
    messages.value.push({
        id: generateId(),
        role: "assistant",
        content:
            "Welcome to ChatGXY. Ask about tools, workflows, errors, or data quality " +
            "and your question will be routed to the appropriate specialist agent.",
        timestamp: new Date(),
        agentType: "router",
        confidence: "high",
        feedback: null,
        isSystemMessage: true,
    });
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
            const metadata = message.agentResponse?.metadata;
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
    const metadata = message.agentResponse?.metadata;
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

function populateAssistantMessage(
    target: Message,
    payload: any,
    fallbackAgentType: string,
    options?: { skipDatasetUpdate?: boolean },
) {
    const agentResponse = (payload?.agent_response ?? payload?.response?.agent_response) as any;
    const rawContent =
        typeof payload === "string" ? payload : (payload?.response ?? agentResponse?.content ?? "No response received");
    const content = typeof rawContent === "string" ? rawContent : String(rawContent ?? "No response received");
    const effectiveAgentType =
        agentResponse?.agent_type || (fallbackAgentType === "auto" ? "router" : fallbackAgentType);

    target.content = content;
    target.timestamp = payload?.timestamp ? new Date(payload.timestamp) : new Date();
    target.agentType = effectiveAgentType;
    target.confidence = agentResponse?.confidence || (payload?.confidence as ConfidenceLevel) || "medium";
    target.feedback = target.feedback ?? null;
    target.agentResponse = agentResponse;
    target.suggestions = normaliseSuggestions(agentResponse?.suggestions);
    target.routingInfo = payload?.routing_info;

    const metadata = agentResponse?.metadata;
    if (metadata) {
        const steps = normaliseAnalysisSteps(metadata.analysis_steps);
        if (steps.length) {
            target.analysisSteps = steps;
        }
        const artifactSource = metadata.artifacts ?? metadata.execution?.artifacts;
        const storedArtifacts = normaliseArtifactList(artifactSource);
        updateMessageOutputsFromArtifacts(target, storedArtifacts);
        const plotEntries = normalisePathList(metadata.plots);
        if (plotEntries.length) {
            target.generatedPlots = plotEntries;
        }
        const fileEntries = normalisePathList(metadata.files);
        if (fileEntries.length) {
            target.generatedFiles = fileEntries;
        }
        const executedTask = metadata.executed_task;
        if (executedTask?.task_id) {
            const taskId = String(executedTask.task_id);
            deliveredTaskIds.add(taskId);
            pyodideTaskToMessage.set(taskId, target);
        }
        const pendingTask = metadata.pyodide_task;
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

function isAwaitingExecution(message: Message): boolean {
    const metadata = message.agentResponse?.metadata;
    if (!metadata) {
        return false;
    }
    const status = typeof metadata.pyodide_status === "string" ? metadata.pyodide_status : undefined;
    return Boolean(status && status !== "completed" && status !== "error" && status !== "timeout");
}

// ── Pyodide execution ─────────────────────────────────────────────────────────
function maybeRunPyodideForMessage(message: Message) {
    const metadata = message.agentResponse?.metadata;
    if (!metadata) {
        return;
    }
    const task = metadata.pyodide_task;
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
        if (existing.status === "completed" || existing.status === "error") {
            metadata.pyodide_status = existing.status;
            return;
        }
        return;
    }

    const status = metadata.pyodide_status;
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
        const metadata = message.agentResponse?.metadata;
        if (!metadata) {
            return;
        }
        const task = metadata.pyodide_task;
        if (!task) {
            return;
        }
        const status = metadata.pyodide_status || "pending";
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

// ── WebSocket streaming ───────────────────────────────────────────────────────
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

// ── Artifact helpers ──────────────────────────────────────────────────────────
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

        const uploadedPayload = (await response.json()) as UploadedArtifact;
        if (uploadedPayload.download_url) {
            uploadedPayload.download_url = resolveDownloadUrl(uploadedPayload.download_url);
        }
        results.push(uploadedPayload);
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

    const { data, error } = await GalaxyApi().POST(`/api/chat/exchange/{exchange_id}/pyodide_result`, {
        params: {
            path: { exchange_id: currentChatId.value },
        },
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
            name: record.name ? String(record.name) : "",
            size: typeof record.size === "number" ? record.size : Number(record.size) || 0,
            mime_type: record.mime_type ? String(record.mime_type) : "",
            download_url: downloadUrl || "",
            history_id: record.history_id ? String(record.history_id) : "",
        });
    }
    return artifacts;
}

function formatGeneratedEntry(entry: string): string {
    return entry.replace(/^generated_file\//, "");
}

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
            agent_type: message.agentType || selectedAgentType.value,
            confidence: message.confidence || "medium",
            content: message.content,
        };
    }
    const metadata = message.agentResponse?.metadata || {};
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
        metadata.executed_task = {
            code: metadata.executed_task?.code || "",
            timeout_seconds: metadata.executed_task?.timeout_seconds || 30,
            task_id: execResult.task_id,
        };
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
            const type = step.type;
            if (type !== "thought" && type !== "action" && type !== "observation" && type !== "conclusion") {
                return null;
            }
            const content = String(step.content ?? "");
            const requirements = Array.isArray(step.requirements) ? step.requirements.map(String) : null;
            const statusValue = step.status;
            const status: AnalysisStep["status"] =
                statusValue === "pending" ||
                statusValue === "running" ||
                statusValue === "completed" ||
                statusValue === "error"
                    ? statusValue
                    : null;
            const stdout = typeof step.stdout === "string" ? step.stdout : null;
            const stderr = typeof step.stderr === "string" ? step.stderr : null;
            const success = typeof step.success === "boolean" ? step.success : null;
            return {
                type,
                content,
                requirements,
                status: type === "action" ? (status ?? "pending") : status,
                stdout,
                stderr,
                success,
            } as AnalysisStep;
        })
        .filter((step): step is AnalysisStep => Boolean(step));
}

// ── API calls ─────────────────────────────────────────────────────────────────
async function submitQuery() {
    if (isChatBusy.value) {
        return;
    }
    if (!query.value.trim()) {
        return;
    }
    pendingCollapsedMessages.length = 0;

    const userMessage: ChatMessage = {
        id: generateId(),
        role: "user",
        content: query.value,
        timestamp: new Date(),
        feedback: null,
    };

    messages.value.push(userMessage);
    const currentQuery = query.value;
    query.value = "";

    await nextTick();
    scrollToBottom(chatContainer.value);

    busy.value = true;

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
                dataset_ids: allowFetchingDatasets.value ? selectedDatasets.value : undefined,
            },
        });

        if (error) {
            const errorText = errorMessageAsString(error, "Failed to get response from ChatGXY.");
            const errorMsg: ChatMessage = {
                id: generateId(),
                role: "assistant",
                content: `Error: ${errorMessage.value}`,
                timestamp: new Date(),
                agentType: selectedAgentType.value,
                confidence: "low",
                feedback: null,
            };
            messages.value.push(errorMsg);

            await nextTick();
            scrollToBottom(chatContainer.value);
        } else if (data) {
            const agentResponse = data.agent_response;
            const content = data.response || "No response received";

            if (data.exchange_id) {
                currentChatId.value = data.exchange_id;
            }

            const assistantMessage: ChatMessage = {
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

            await nextTick();
            scrollToBottom(chatContainer.value);
        }
    } catch (e) {
        console.error("Unexpected chat error:", e);
        const errorMsg: ChatMessage = {
            id: generateId(),
            role: "assistant",
            content: "Unexpected error occurred. Please try again.",
            timestamp: new Date(),
            agentType: selectedAgentType.value,
            confidence: "low",
            feedback: null,
        };
        messages.value.push(errorMsg);

        await nextTick();
        scrollToBottom(chatContainer.value);
    } finally {
        busy.value = false;
        await nextTick();
        scrollToBottom(chatContainer.value);
    }
}

async function sendFeedback(messageId: string, value: "up" | "down") {
    const message = messages.value.find((m) => m.id === messageId);
    if (message) {
        message.feedback = value;

        if (currentChatId.value) {
            try {
                const feedbackValue = value === "up" ? 1 : 0;
                const { error } = await GalaxyApi().PUT("/api/chat/exchange/{exchange_id}/feedback", {
                    params: {
                        path: { exchange_id: currentChatId.value },
                    },
                    body: feedbackValue,
                });

                if (error) {
                    console.error("Failed to save feedback:", error);
                    message.feedback = null;
                }
            } catch (e) {
                console.error("Failed to save feedback:", e);
                message.feedback = null;
            }
        }
    }
}

async function fetchConversation(exchangeId: string): Promise<boolean> {
    const { data: fullConversation } = await GalaxyApi().GET(`/api/chat/exchange/{exchange_id}/messages`, {
        params: {
            path: { exchange_id: exchangeId },
        },
    });

    if (!fullConversation || fullConversation.length === 0) {
        return false;
    }

    messages.value = fullConversation.map((msg: any, index: number) => {
        const message: Message = {
            id: `hist-${msg.role}-${exchangeId}-${index}`,
            role: msg.role as "user" | "assistant",
            content: msg.content,
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
            }
        }

        return message;
    });

    const numericId = parseInt(exchangeId, 10);
    currentChatId.value = isNaN(numericId) ? null : numericId;
    nextTick(() => scrollToBottom(chatContainer.value));
    return true;
}

async function loadChatById(exchangeId: string) {
    try {
        const loaded = await fetchConversation(exchangeId);
        if (loaded) {
            hasLoadedInitialChat.value = true;
        }
    } catch (e) {
        console.error("Failed to load chat by ID:", e);
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

function startNewChat() {
    pendingCollapsedMessages.length = 0;
    messages.value = [
        {
            id: generateId(),
            role: "assistant",
            content: "New conversation started. How can I help?",
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

async function deleteCurrentChat() {
    if (!currentChatId.value) {
        return;
    }
    try {
        const { error } = await GalaxyApi().DELETE("/api/chat/exchange/{exchange_id}", {
            params: { path: { exchange_id: currentChatId.value } },
        });
        if (!error) {
            startNewChat();
        }
    } catch (e) {
        console.error("Failed to delete chat:", e);
    }
}

function popOutToScratchbook() {
    const Galaxy = getGalaxyInstance();
    const path = currentChatId.value ? `/chatgxy/${currentChatId.value}` : "/chatgxy";
    const url = `${path}?compact=true`;
    Galaxy.frame.add({ title: "ChatGXY", url });
}

// ── History sidebar ───────────────────────────────────────────────────────────
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
            chatHistory.value = [];
            if (currentChatId.value) {
                startNewChat();
            }
        } else if (error) {
            console.error("Failed to clear history:", error);
        }
    } catch (e) {
        console.error("Failed to clear history:", e);
    }
}

async function loadPreviousChat(item: ChatHistoryItem) {
    pendingCollapsedMessages.length = 0;
    try {
        const { data } = await GalaxyApi().GET(`/api/chat/exchange/{exchange_id}/messages`, {
            params: { path: { exchange_id: item.id } },
        });

        const fullConversation = data as any[] | undefined;
        if (fullConversation && fullConversation.length > 0) {
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
                        const metadata = msg.agent_response?.metadata;
                        const steps = metadata ? normaliseAnalysisSteps(metadata?.analysis_steps) : [];
                        if (steps.length) {
                            message.analysisSteps = steps;
                        }
                        if (metadata) {
                            const artifactSource = metadata?.artifacts ?? metadata?.execution?.artifacts;
                            const storedArtifacts = normaliseArtifactList(artifactSource);
                            updateMessageOutputsFromArtifacts(message, storedArtifacts);
                            const plots = normalisePathList(metadata?.plots);
                            message.generatedPlots = plots.length ? plots : undefined;
                            const files = normalisePathList(metadata?.files);
                            message.generatedFiles = files.length ? files : undefined;
                            const executedTask = metadata?.executed_task;
                            if (executedTask?.task_id) {
                                deliveredTaskIds.add(String(executedTask.task_id));
                                pyodideTaskToMessage.set(String(executedTask.task_id), message);
                                taskIdToMessage[String(executedTask.task_id)] = message;
                            }
                            const pendingTask = metadata?.pyodide_task;
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
            loadSingleMessageFallback(item);
        }

        currentChatId.value = item.id;
        showHistory.value = false;
        nextTick(() => scrollToBottom(chatContainer.value));
    } catch (error) {
        console.error("Error loading full conversation:", error);
        loadSingleMessageFallback(item);
    }
}

function loadSingleMessageFallback(item: ChatHistoryItem) {
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
        const metadata = item.agent_response?.metadata;
        const steps = metadata ? normaliseAnalysisSteps(metadata?.analysis_steps) : [];
        if (steps.length) {
            assistantMessage.analysisSteps = steps;
        }
        if (metadata) {
            const artifactSource = metadata?.artifacts ?? metadata?.execution?.artifacts;
            const storedArtifacts = normaliseArtifactList(artifactSource);
            updateMessageOutputsFromArtifacts(assistantMessage, storedArtifacts);
            const plots = normalisePathList(metadata?.plots);
            if (plots.length) {
                assistantMessage.generatedPlots = plots;
            }
            const files = normalisePathList(metadata?.files);
            if (files.length) {
                assistantMessage.generatedFiles = files;
            }
            const executedTask = metadata?.executed_task;
            if (executedTask?.task_id) {
                deliveredTaskIds.add(String(executedTask.task_id));
                pyodideTaskToMessage.set(String(executedTask.task_id), assistantMessage);
            }
            const pendingTask = metadata?.pyodide_task;
            if (pendingTask?.task_id) {
                pyodideTaskToMessage.set(String(pendingTask.task_id), assistantMessage);
            }
        }
    }

    applyCollapseState(assistantMessage);
    messages.value = [userMessage, assistantMessage];
    currentChatId.value = item.id;
    showHistory.value = false;
    nextTick(() => scrollToBottom(chatContainer.value));
    maybeRunPyodideForMessage(assistantMessage);
}

async function deleteCurrentChat() {
    if (!currentChatId.value) {
        return;
    }
    try {
        const { error } = await GalaxyApi().DELETE("/api/chat/exchange/{exchange_id}", {
            params: { path: { exchange_id: currentChatId.value } },
        });
        if (!error) {
            startNewChat();
        }
    } catch (e) {
        console.error("Failed to delete chat:", e);
    }
}

function popOutToScratchbook() {
    const Galaxy = getGalaxyInstance();
    const path = currentChatId.value ? `/chatgxy/${currentChatId.value}` : "/chatgxy";
    const url = `${path}?compact=true`;
    Galaxy.frame.add({ title: "ChatGXY", url });
}
</script>

<template>
    <div class="chatgxy-container" :class="{ 'chatgxy-compact': compact }">
        <div v-if="!compact" class="chatgxy-header">
            <div class="header-main">
                <Heading h2 :icon="faMagic" size="lg">
                    <span>ChatGXY</span>
                </Heading>
                <div class="header-actions">
                    <GButton
                        color="blue"
                        :outline="!allowFetchingDatasets"
                        size="small"
                        :title="
                            !allowFetchingDatasets
                                ? 'Include datasets from my current history in the conversation context'
                                : 'Do not include datasets'
                        "
                        @click="() => (allowFetchingDatasets = !allowFetchingDatasets)">
                        <FontAwesomeIcon :icon="faMicroscope" fixed-width />
                        Include Datasets
                    </GButton>

                    <GButton color="blue" outline size="small" title="Start New Chat" @click="startNewChat">
                        <FontAwesomeIcon :icon="faPlus" fixed-width />
                        New
                    </GButton>

                    <button
                        v-if="currentChatId"
                        class="btn btn-sm btn-outline-danger"
                        title="Delete this conversation"
                        @click="deleteCurrentChat">
                        <FontAwesomeIcon :icon="faTrash" fixed-width />
                    </button>

                    <button
                        class="btn btn-sm btn-outline-primary"
                        title="Open in floating window"
                        @click="popOutToScratchbook">
                        <FontAwesomeIcon :icon="faExternalLinkAlt" fixed-width />
                    </button>

                    <GButton
                        color="blue"
                        :outline="!showHistory"
                        size="small"
                        :title="showHistory ? 'Hide History' : 'Show History'"
                        @click="toggleHistory">
                        <FontAwesomeIcon :icon="faHistory" fixed-width />
                    </GButton>
                </div>
            </div>

            <div v-if="allowFetchingDatasets" class="header-expand">
                <div class="pb-2">Select a dataset for this chat</div>
                <DatasetSelector
                    v-if="datasetOptions.length"
                    id="dataset-select"
                    v-model="selectedDatasetsFormData"
                    :loading="loadingDatasets"
                    :options="formDataOptions"
                    user-defined-title="Created for ChatGXY"
                    workflow-run />
                <BAlert v-else :variant="datasetError ? 'danger' : 'info'" show>
                    <div v-if="loadingDatasets">
                        <LoadingSpan message="Loading datasets" />
                    </div>
                    <div v-else-if="datasetError">{{ datasetError }}</div>
                    <div v-else>
                        No datasets in the current history. Upload a dataset or switch to a different history to use
                        this feature.
                    </div>
                </BAlert>
            </div>
        </div>

        <div class="chatgxy-body">
            <!-- History Sidebar -->
            <div v-if="showHistory && !compact" class="history-sidebar">
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
            <div ref="chatContainer" class="chat-messages">
                <ChatMessageCell
                    v-for="message in messages"
                    :key="message.id"
                    :message="message"
                    :render-markdown="safeRenderMarkdown"
                    :processing-action="processingAction"
                    @feedback="sendFeedback"
                    @handle-action="handleAction">
                    <template v-slot:after-content>
                        <div v-if="isAwaitingExecution(message)" class="alert alert-warning pyodide-hint mb-2">
                            ⚙️ Analysis still running… please keep this tab open; refreshing will restart the execution.
                        </div>
                        <div
                            v-else-if="message.agentResponse?.metadata?.pyodide_status === 'timeout'"
                            class="alert alert-warning pyodide-hint mb-2">
                            ⚠️ Previous run timed out before the result was sent. Please ask again if you still need
                            this step to complete.
                        </div>
                        <MessageArtifacts v-if="hasArtifacts(message)" :message="message" />
                        <MessageIntermediateDetails :message="message" :pyodide-executions="pyodideExecutions" />
                    </template>
                </ChatMessageCell>

                <!-- Loading state -->
                <div v-if="busy" class="loading-entry">
                    <div class="loading-gutter">
                        <span class="loading-indicator">
                            <FontAwesomeIcon :icon="getAgentIcon(selectedAgentType)" fixed-width />
                        </span>
                    </div>
                    <div class="loading-body">
                        <BSkeleton animation="wave" width="85%" />
                        <BSkeleton animation="wave" width="55%" />
                        <BSkeleton animation="wave" width="70%" />
                    </div>
                </div>
            </div>
        </div>

        <div class="chatgxy-footer">
            <ChatInput :value="query" :busy="isChatBusy" @input="query = $event" @submit="submitQuery" />
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
    border-radius: 0.5rem;
    overflow: hidden;
}

.chatgxy-compact {
    height: 100vh;

    .chat-messages {
        padding: 0.75rem 1rem;
    }

    .chatgxy-footer {
        padding: 0.5rem 0.75rem;
    }
}

.chatgxy-header {
    padding: 0.75rem 1rem;
    background: $panel-bg-color;
    border-bottom: $border-default;

    .header-main {
        display: flex;
        align-items: center;
        justify-content: space-between;
    }

    .header-actions {
        display: flex;
        gap: 0.5rem;
        align-items: center;
    }

    .header-expand {
        margin-top: 0.625rem;
        padding-top: 0.625rem;
        border-top: 1px solid rgba($brand-primary, 0.12);
        animation: fadeIn 0.2s ease-out;

        > div:first-child {
            font-size: 0.72rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            color: $text-muted;
        }
    }
}

.chatgxy-footer {
    padding: 0.75rem 1rem;
    background: $panel-bg-color;
    border-top: $border-default;
    box-shadow: 0 -2px 4px rgba(0, 0, 0, 0.05);
}

.chat-messages {
    flex: 1;
    overflow-y: auto;
    padding: 1rem 1.5rem;
    background: $white;
}

.pyodide-hint {
    font-size: 0.85rem;
}

// Loading skeleton
.loading-entry {
    display: flex;
    gap: 0;
    margin-top: 1.25rem;
    animation: fadeIn 0.2s ease-out;
}

.loading-gutter {
    flex-shrink: 0;
    width: 2rem;
    padding-top: 0.125rem;
}

.loading-indicator {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 1.5rem;
    height: 1.5rem;
    border-radius: 50%;
    background: rgba($brand-primary, 0.08);
    color: $brand-primary;
    font-size: 0.65rem;
}

.loading-body {
    flex: 1;
    opacity: 0.6;
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
</style>
