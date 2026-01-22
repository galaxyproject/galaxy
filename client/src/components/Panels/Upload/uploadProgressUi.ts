import type { IconDefinition } from "@fortawesome/fontawesome-svg-core";
import { faCheck, faExclamationTriangle, faLayerGroup, faSpinner, faTimes } from "@fortawesome/free-solid-svg-icons";

import type { UploadItem } from "@/composables/upload/uploadItemTypes";

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

const BATCH_PROGRESS_UI = {
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
} as const satisfies Record<BatchStatus, (batch: BatchWithProgress) => BatchProgressUi>;

export function getBatchProgressUi(batch: BatchWithProgress): BatchProgressUi {
    return BATCH_PROGRESS_UI[batch.status](batch);
}
