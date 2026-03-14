import { useToast } from "@/composables/toast";
import { getAppRoot } from "@/onload/loadConfig";

import type { AnalysisStep, ChatMessage, UploadedArtifact } from "./types";

export function applyCollapseState(message: ChatMessage) {
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

export function downloadArtifact(artifact: UploadedArtifact) {
    const Toast = useToast();

    if (artifact.download_url) {
        window.open(artifact.download_url, "_blank");
        return;
    }
    Toast.info("Artifact download is not available yet.");
}

export function escapeHtml(raw: string): string {
    return raw
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

export function formatGeneratedEntry(entry: string): string {
    return entry.replace(/^generated_file\//, "");
}

export function formatSize(size?: number): string {
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

export function generateId(): string {
    return `msg-${Date.now()}-${Math.random().toString(36).substring(2, 11)}`;
}

/** Type guard to check if a message has artifacts */
export function hasArtifacts(
    message: ChatMessage,
): message is ChatMessage & { artifacts: NonNullable<ChatMessage["artifacts"]> } {
    return Boolean(message.artifacts && message.artifacts.length > 0);
}

/** Type guard to check if a message has collapsed history with at least one entry */
export function hasCollapsedHistory(
    message: ChatMessage,
): message is ChatMessage & { collapsedHistory: NonNullable<ChatMessage["collapsedHistory"]> } {
    return Boolean(message.collapsedHistory && message.collapsedHistory.length > 0);
}

export function isAwaitingExecution(message: ChatMessage): boolean {
    const metadata = message.agentResponse?.metadata;
    if (!metadata) {
        return false;
    }
    const status = typeof metadata.pyodide_status === "string" ? metadata.pyodide_status : undefined;
    return Boolean(status && status !== "completed" && status !== "error" && status !== "timeout");
}

export function isDataAnalysisMessage(message?: ChatMessage): boolean {
    if (!message) {
        return false;
    }
    const agentType = message.agentType || message.agentResponse?.agent_type;
    return typeof agentType === "string" && agentType.startsWith("data_analysis");
}

export function normaliseAnalysisSteps(raw: unknown): AnalysisStep[] {
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

export function normaliseArtifactList(raw: unknown): UploadedArtifact[] {
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

export function normalisePathList(raw: unknown): string[] {
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

export function resolveDownloadUrl(url: string): string {
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

export function scrollToBottom(container: HTMLElement | undefined): void {
    if (container) {
        container.scrollTo({
            top: container.scrollHeight,
            behavior: "auto",
        });
    }
}

export function shouldAutoCollapse(message: ChatMessage): boolean {
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
