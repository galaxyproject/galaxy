import { computed } from "vue";

import type { FetchDatasetHash } from "@/api/tools";
import { useUserLocalStorage } from "@/composables/userLocalStorage";

import type { UploadMode } from "./types";

const LOCAL_STORAGE_KEY = "uploadPanel.activeUploads";

/** Upload lifecycle status */
export type UploadStatus = "queued" | "uploading" | "processing" | "completed" | "error";

/** Internal state tracking for an upload */
interface UploadState {
    id: string;
    status: UploadStatus;
    progress: number;
    error?: string;
    createdAt: number;
}

/** Common properties shared by all upload item types */
interface UploadItemCommon {
    uploadMode: UploadMode;
    name: string;
    size: number;
    targetHistoryId: string;
    dbkey: string;
    extension: string;
    spaceToTab: boolean;
    toPosixLines: boolean;
    deferred: boolean;
    hashes?: FetchDatasetHash[];
}

/** Upload item from a local file */
export interface LocalFileUploadItem extends UploadItemCommon {
    uploadMode: "local-file";
    /** File handle (not persisted in localStorage) */
    fileData?: File;
}

/** Upload item from pasted text content */
export interface PastedContentUploadItem extends UploadItemCommon {
    uploadMode: "paste-content";
    content: string;
}

/** Upload item from a URL */
export interface UrlUploadItem extends UploadItemCommon {
    uploadMode: "paste-links";
    url: string;
}

export type NewUploadItem = LocalFileUploadItem | PastedContentUploadItem | UrlUploadItem;

/** Upload item with state tracking */
export type UploadItem = NewUploadItem & UploadState;

function generateId() {
    return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

// Shared state - initialized lazily on first use
let activeItems: ReturnType<typeof useUserLocalStorage<UploadItem[]>> | null = null;

function getActiveItems() {
    if (!activeItems) {
        activeItems = useUserLocalStorage<UploadItem[]>(LOCAL_STORAGE_KEY, []);
    }
    return activeItems;
}

/**
 * Composable for managing upload state and progress tracking.
 * Persists upload items to user-specific localStorage and provides
 * reactive state for upload monitoring.
 */
export function useUploadState() {
    const items = getActiveItems();

    const hasUploads = computed(() => items.value.length > 0);

    const completedCount = computed(() => items.value.filter((i) => i.status === "completed").length);
    const errorCount = computed(() => items.value.filter((i) => i.status === "error").length);
    const uploadingCount = computed(
        () => items.value.filter((i) => i.status === "uploading" || i.status === "processing").length,
    );
    const isUploading = computed(() => items.value.some((i) => i.status === "uploading" || i.status === "processing"));

    const totalProgress = computed(() => {
        if (items.value.length === 0) {
            return 0;
        }
        const sum = items.value.reduce((acc, file) => acc + file.progress, 0);
        return Math.round(sum / items.value.length);
    });

    const totalSizeBytes = computed(() => items.value.reduce((sum, file) => sum + file.size, 0));

    const uploadedSizeBytes = computed(() =>
        items.value.reduce((sum, file) => sum + (file.size * file.progress) / 100, 0),
    );

    const hasCompleted = computed(() => items.value.some((u) => u.status === "completed"));
    /**
     * Adds a new upload item to the queue.
     * @param item - Upload configuration (file, URL, or pasted content)
     * @returns Unique identifier for the upload
     */
    function addUploadItem(item: NewUploadItem) {
        const entry = {
            ...item,
            id: generateId(),
            createdAt: Date.now(),
            progress: 0,
            status: "queued",
            error: undefined,
        } satisfies UploadItem;

        items.value.push(entry);
        return entry.id;
    }

    /**
     * Updates upload progress for a specific item.
     * Automatically marks as completed when progress reaches 100%.
     * @param id - Upload item identifier
     * @param progress - Progress percentage (0-100)
     */
    function updateProgress(id: string, progress: number) {
        const item = items.value.find((u) => u.id === id);
        if (item) {
            item.progress = Math.max(0, Math.min(100, Math.round(progress)));
            if (item.progress >= 100 && item.status !== "error") {
                item.status = "completed";
            }
        }
    }

    /**
     * Updates the status of an upload item.
     * @param id - Upload item identifier
     * @param status - New status to set
     */
    function setStatus(id: string, status: UploadStatus) {
        const item = items.value.find((u) => u.id === id);
        if (item) {
            item.status = status;
        }
    }

    /**
     * Marks an upload as failed with an error message.
     * @param id - Upload item identifier
     * @param error - Error message describing the failure
     */
    function setError(id: string, error: string) {
        const item = items.value.find((u) => u.id === id);
        if (item) {
            item.status = "error";
            item.error = error;
        }
    }

    /**
     * Removes all completed uploads from the list.
     */
    function clearCompleted() {
        items.value = items.value.filter((u) => u.status !== "completed");
    }

    /**
     * Clears all upload items from the list.
     */
    function clearAll() {
        items.value = [];
    }

    return {
        activeItems: items,
        hasUploads,
        completedCount,
        errorCount,
        uploadingCount,
        isUploading,
        totalProgress,
        totalSizeBytes,
        uploadedSizeBytes,
        hasCompleted,
        addUploadItem,
        updateProgress,
        setStatus,
        setError,
        clearCompleted,
        clearAll,
    };
}
