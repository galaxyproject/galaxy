import type { IconDefinition } from "@fortawesome/fontawesome-svg-core";
import {
    faCheck,
    faCloud,
    faExclamationTriangle,
    faLayerGroup,
    faSpinner,
    faTimes,
} from "@fortawesome/free-solid-svg-icons";

import type { UploadItem } from "@/composables/upload/uploadItemTypes";

import type { UploadMethod } from "./types";
import { getUploadMethod } from "./uploadMethodRegistry";
import type { BatchStatus, CollectionBatchState } from "./uploadState";

/**
 * Shared UI contract for progress indicators (files & batches)
 */
interface ProgressUiBase {
    icon: IconDefinition;
    textClass: string;
    barClass?: string;
    spin: boolean;
}

/**
 * UI representation of a single upload file
 */
export interface FileProgressUi extends ProgressUiBase {}

/**
 * UI representation of a batch / collection upload
 */
export interface BatchProgressUi extends ProgressUiBase {
    label: string;
}

/**
 * Batch state as used by the upload progress view (includes progress percentage)
 */
export interface BatchWithProgress extends CollectionBatchState {
    progress: number;
}

const FILE_PROGRESS_UI: Record<UploadItem["status"], FileProgressUi> = {
    queued: {
        icon: faSpinner,
        textClass: "text-muted",
        spin: false,
    },
    uploading: {
        icon: faSpinner,
        textClass: "text-primary",
        spin: true,
    },
    processing: {
        icon: faSpinner,
        textClass: "text-primary",
        spin: true,
    },
    completed: {
        icon: faCheck,
        textClass: "text-success",
        barClass: "bg-success",
        spin: false,
    },
    error: {
        icon: faTimes,
        textClass: "text-danger",
        barClass: "bg-danger",
        spin: false,
    },
} as const;

export function getFileProgressUi(file: UploadItem): FileProgressUi {
    return FILE_PROGRESS_UI[file.status];
}

const BATCH_PROGRESS_UI: Record<BatchStatus, (batch: BatchWithProgress) => BatchProgressUi> = {
    uploading: (batch) => ({
        icon: faLayerGroup,
        textClass: "text-primary",
        spin: false,
        label: `${batch.progress}% uploaded`,
    }),
    "creating-collection": () => ({
        icon: faSpinner,
        textClass: "text-info",
        barClass: "bg-info",
        spin: true,
        label: "Creating collection...",
    }),
    completed: () => ({
        icon: faCheck,
        textClass: "text-success",
        spin: false,
        label: "Collection created",
    }),
    error: () => ({
        icon: faExclamationTriangle,
        textClass: "text-danger",
        barClass: "bg-danger",
        spin: false,
        label: "Error",
    }),
} as const;

export function getBatchProgressUi(batch: BatchWithProgress): BatchProgressUi {
    return BATCH_PROGRESS_UI[batch.status](batch);
}

export interface UploadItemDisplayBadge {
    id: string;
    label: string;
    title: string;
    icon?: IconDefinition;
    variant: "info" | "secondary" | "primary" | "warning" | "danger";
}

export interface UploadItemDisplayInfo {
    icon?: IconDefinition;
    iconTitle?: string;
    badges: UploadItemDisplayBadge[];
}

/**
 * Get display information for an upload item (method icon, deferred badge, etc.).
 */
export function getUploadItemDisplayInfo(item: UploadItem): UploadItemDisplayInfo {
    const badges: UploadItemDisplayBadge[] = [];

    // Add deferred badge if applicable
    if (item.deferred) {
        badges.push({
            id: "deferred",
            label: "Deferred",
            title: "This file will be downloaded when needed by a job",
            icon: faCloud,
            variant: "info",
        });
    }

    // Get upload method icon and name
    const uploadMethod = getUploadMethod(item.uploadMode);

    return {
        icon: uploadMethod?.icon,
        iconTitle: uploadMethod?.name,
        badges,
    };
}

export interface BatchDisplayInfo {
    uploadModeSummary: string;
    hasMultipleModes: boolean;
    allDeferred: boolean;
}

/**
 * Extended batch state with uploads included.
 */
export interface BatchWithUploads extends CollectionBatchState {
    uploads: UploadItem[];
}

/**
 * Batch with both progress tracking and uploads (used in progress view).
 */
export interface BatchWithProgressAndUploads extends BatchWithProgress {
    uploads: UploadItem[];
    allCompleted: boolean;
    hasError: boolean;
}

/**
 * Get aggregated display information for a batch (upload mode summary, deferred status).
 */
export function getBatchDisplayInfo(batch: BatchWithUploads): BatchDisplayInfo {
    const uploads = batch.uploads;
    const uploadModes = new Set(uploads.map((u: UploadItem) => u.uploadMode));
    const deferredCount = uploads.filter((u: UploadItem) => u.deferred).length;

    // Create summary of upload modes
    let uploadModeSummary = "";
    if (uploadModes.size === 1) {
        const mode = Array.from(uploadModes)[0] as UploadMethod;
        const methodConfig = getUploadMethod(mode);
        uploadModeSummary = methodConfig?.name || mode;
    } else {
        // Multiple modes - show counts by type
        const modeCounts = new Map<string, number>();
        uploads.forEach((u: UploadItem) => {
            const count = modeCounts.get(u.uploadMode) || 0;
            modeCounts.set(u.uploadMode, count + 1);
        });

        const summaryParts: string[] = [];
        modeCounts.forEach((count, mode) => {
            const methodConfig = getUploadMethod(mode as UploadMethod);
            const name = methodConfig?.name || mode;
            summaryParts.push(`${count} ${name}`);
        });
        uploadModeSummary = summaryParts.join(", ");
    }

    return {
        uploadModeSummary,
        hasMultipleModes: uploadModes.size > 1,
        allDeferred: deferredCount === uploads.length && uploads.length > 0,
    };
}

/**
 * Get progress breakdown summary for a batch (e.g., "3/5 completed, 1 error").
 */
export function getBatchProgressSummary(batch: BatchWithUploads): string {
    const total = batch.uploads.length;
    const completed = batch.uploads.filter((u: UploadItem) => u.status === "completed").length;
    const errors = batch.uploads.filter((u: UploadItem) => u.status === "error").length;

    const parts: string[] = [];

    parts.push(`${completed}/${total} completed`);

    if (errors > 0) {
        parts.push(`${errors} error${errors > 1 ? "s" : ""}`);
    }

    return parts.join(", ");
}
