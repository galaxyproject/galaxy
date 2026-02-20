import { useToast } from "@/composables/toast";

import type { Message, UploadedArtifact } from "./types";

export function collapsedSummary(message: Message): string {
    const metadata = message.agentResponse?.metadata;
    if (metadata?.summary && typeof metadata.summary === "string") {
        return metadata.summary;
    }
    const content = (message.content || "").trim();
    return content.split("\n")[0] || "Previous step";
}

export function downloadArtifact(artifact: UploadedArtifact) {
    const Toast = useToast();

    if (artifact.download_url) {
        window.open(artifact.download_url, "_blank");
        return;
    }
    Toast.info("Artifact download is not available yet.");
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

/** Type guard to check if a message has artifacts */
export function hasArtifacts(message: Message): message is Message & { artifacts: NonNullable<Message["artifacts"]> } {
    return Boolean(message.artifacts && message.artifacts.length > 0);
}

/** Type guard to check if a message has collapsed history with at least one entry */
export function hasCollapsedHistory(
    message: Message,
): message is Message & { collapsedHistory: NonNullable<Message["collapsedHistory"]> } {
    return Boolean(message.collapsedHistory && message.collapsedHistory.length > 0);
}

export function isDataAnalysisMessage(message?: Message): boolean {
    if (!message) {
        return false;
    }
    const agentType = message.agentType || message.agentResponse?.agent_type;
    return typeof agentType === "string" && agentType.startsWith("data_analysis");
}
