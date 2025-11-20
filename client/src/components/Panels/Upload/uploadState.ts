import { ref } from "vue";

import type { FetchDatasetHash, UploadElement } from "@/api/upload";

import type { UploadMode } from "./types";

export type UploadStatus = "queued" | "uploading" | "processing" | "completed" | "error";

// Internal upload item tracked in state
export interface UploadItem {
    id: string;
    uploadMethod: UploadMode;
    element: UploadElement; // discriminated by element.src
    targetHistoryId: string;
    fileData?: File; // only for src === "files"
    name: string; // convenient UI label (filename, URL, or "Pasted content")
    size: number; // bytes, 0 if unknown
    progress: number; // 0..100
    status: UploadStatus;
    error?: string;
    createdAt: number;
}

const LOCAL_STORAGE_KEY = "uploadPanel.activeUploads";

// Shared defaults/options used when enqueueing items
export interface ElementDefaults {
    dbkey: string;
    ext: string;
    space_to_tab: boolean;
    to_posix_lines: boolean;
    deferred: boolean;
    name?: string | number | boolean | null;
    hashes?: FetchDatasetHash[] | null;
}

export interface EnqueueOptions {
    uploadMethod: UploadMode;
    targetHistoryId: string;
    elementDefaults: ElementDefaults;
}

export type NewUploadItem = Omit<UploadItem, "id" | "createdAt" | "progress" | "status" | "error">;

function generateId() {
    return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

function loadPersistedItems(): UploadItem[] {
    try {
        const raw = localStorage.getItem(LOCAL_STORAGE_KEY);
        if (!raw) {
            return [];
        }
        const parsed = JSON.parse(raw) as UploadItem[];
        // On reload, we cannot resume local File handles automatically; keep items but leave fileData undefined
        return parsed.map((i) => ({ ...i, fileData: undefined }));
    } catch {
        return [];
    }
}

function persistItems(items: UploadItem[]) {
    try {
        // Do not persist File handles
        const serializable = items.map(({ fileData: _fd, ...rest }) => rest);
        localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(serializable));
    } catch {
        // ignore persistence failures
    }
}

const activeItems = ref<UploadItem[]>(loadPersistedItems());

export function useUploadState() {
    // Public method to add items (used by service)
    function addUploadItem(item: NewUploadItem) {
        const id = generateId();
        const entry: UploadItem = {
            id,
            createdAt: Date.now(),
            progress: 0,
            status: "queued",
            error: undefined,
            ...item,
        };
        activeItems.value.push(entry);
        persistItems(activeItems.value);
        return entry.id;
    }

    // Public helpers to enqueue different sources
    function enqueueLocalFiles(files: File[], opts: EnqueueOptions) {
        files.forEach((file) => {
            const element = {
                src: "files" as const,
                name: file.name,
                dbkey: opts.elementDefaults.dbkey,
                ext: opts.elementDefaults.ext,
                space_to_tab: opts.elementDefaults.space_to_tab,
                to_posix_lines: opts.elementDefaults.to_posix_lines,
                deferred: opts.elementDefaults.deferred,
                auto_decompress: true,
            } satisfies UploadElement;
            addUploadItem({
                uploadMethod: opts.uploadMethod,
                element,
                targetHistoryId: opts.targetHistoryId,
                fileData: file,
                name: file.name,
                size: file.size,
            });
        });
    }

    function enqueuePastedContent(content: string, opts: EnqueueOptions) {
        const element = {
            src: "pasted" as const,
            paste_content: content,
            name: opts.elementDefaults.name ?? "Pasted content",
            dbkey: opts.elementDefaults.dbkey,
            ext: opts.elementDefaults.ext,
            space_to_tab: opts.elementDefaults.space_to_tab,
            to_posix_lines: opts.elementDefaults.to_posix_lines,
            deferred: opts.elementDefaults.deferred,
            auto_decompress: true,
        } satisfies UploadElement;
        addUploadItem({
            uploadMethod: opts.uploadMethod,
            element,
            targetHistoryId: opts.targetHistoryId,
            name: String(element.name ?? "Pasted content"),
            size: typeof content === "string" ? new Blob([content]).size : 0,
        });
    }

    function enqueueUrls(urls: string[], opts: EnqueueOptions) {
        urls.map((u) => u.trim())
            .filter((u) => !!u)
            .forEach((url) => {
                const element = {
                    src: "url" as const,
                    url,
                    name: opts.elementDefaults.name ?? url,
                    dbkey: opts.elementDefaults.dbkey,
                    ext: opts.elementDefaults.ext,
                    space_to_tab: opts.elementDefaults.space_to_tab,
                    to_posix_lines: opts.elementDefaults.to_posix_lines,
                    deferred: opts.elementDefaults.deferred,
                    hashes: opts.elementDefaults.hashes,
                    auto_decompress: true,
                } satisfies UploadElement;
                addUploadItem({
                    uploadMethod: opts.uploadMethod,
                    element,
                    targetHistoryId: opts.targetHistoryId,
                    name: url,
                    size: 0,
                });
            });
    }

    function updateProgress(idOrName: string, progress: number) {
        const item = activeItems.value.find((u) => u.id === idOrName || u.name === idOrName);
        if (item) {
            item.progress = Math.max(0, Math.min(100, Math.round(progress)));
            if (item.progress >= 100 && item.status !== "error") {
                item.status = "completed";
            }
            persistItems(activeItems.value);
        }
    }

    function setStatus(id: string, status: UploadStatus) {
        const item = activeItems.value.find((u) => u.id === id);
        if (item) {
            item.status = status;
            persistItems(activeItems.value);
        }
    }

    function setError(idOrName: string, error: string) {
        const item = activeItems.value.find((u) => u.id === idOrName || u.name === idOrName);
        if (item) {
            item.status = "error";
            item.error = error;
            persistItems(activeItems.value);
        }
    }

    function clearCompleted() {
        activeItems.value = activeItems.value.filter((u) => u.status !== "completed");
        persistItems(activeItems.value);
    }

    function clearAll() {
        activeItems.value = [];
        persistItems(activeItems.value);
    }

    return {
        // state
        activeItems,
        // direct item management
        addUploadItem,
        enqueueLocalFiles,
        enqueuePastedContent,
        enqueueUrls,
        // updates
        updateProgress,
        setStatus,
        setError,
        // cleanup
        clearCompleted,
        clearAll,
    };
}
