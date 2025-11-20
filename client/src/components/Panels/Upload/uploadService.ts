import type { DataElementsTarget, FetchPayload, HdaDestination, UploadElement } from "@/api/upload";
import { errorMessageAsString } from "@/utils/simple-error";
import { uploadSubmit } from "@/utils/upload-submit.js";

import type { EnqueueOptions, NewUploadItem } from "./uploadState";
import { useUploadState } from "./uploadState";

interface QueueItem {
    id: string; // UploadItem id from state
}

const queue: QueueItem[] = [];
let processing = false;
const uploadState = useUploadState();

export interface BuiltPayload {
    data: FetchPayload & { auto_decompress: boolean; files?: (File | Blob)[] };
    isComposite: boolean;
}

function buildPayloadForElement(element: UploadElement, historyId: string, fileData?: File): BuiltPayload {
    const target: DataElementsTarget = {
        auto_decompress: true,
        destination: { type: "hdas" } as HdaDestination,
        elements: [element] as unknown as DataElementsTarget["elements"],
    };
    const base: FetchPayload = {
        history_id: historyId,
        targets: [target],
    };
    const data: FetchPayload & { auto_decompress: boolean; files?: (File | Blob)[] } = {
        ...base,
        auto_decompress: true,
    };
    if (element.src === "files" && fileData) {
        data.files = [fileData];
    }
    return { data, isComposite: false };
}

async function processNext() {
    if (processing) {
        return;
    }
    const next = queue.shift();
    if (!next) {
        return;
    }

    processing = true;

    const item = uploadState.activeItems.value.find((i) => i.id === next.id);
    if (!item) {
        processing = false;
        return processNext();
    }

    try {
        uploadState.setStatus(item.id, "uploading");
        const { data, isComposite } = buildPayloadForElement(item.element, item.targetHistoryId, item.fileData);

        await new Promise<void>((resolve) => {
            uploadSubmit({
                data,
                isComposite,
                progress: (p: number) => uploadState.updateProgress(item.id, p),
                success: () => {
                    uploadState.updateProgress(item.id, 100);
                    resolve();
                },
                error: (e: unknown) => {
                    const errorMessage = errorMessageAsString(e);
                    uploadState.setError(item.id, errorMessage);
                    resolve();
                },
            });
        });
    } catch (e) {
        const errorMessage = errorMessageAsString(e);
        uploadState.setError(item.id, errorMessage);
    } finally {
        processing = false;
        processNext();
    }
}

export function useUploadService() {
    function enqueue(id: string) {
        queue.push({ id });
        processNext();
    }

    function enqueueAll(ids: string[]) {
        ids.forEach((id) => queue.push({ id }));
        processNext();
    }

    // High-level methods that handle state internally
    function enqueueLocalFiles(files: File[], opts: EnqueueOptions) {
        const ids: string[] = [];
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
            const item: NewUploadItem = {
                uploadMethod: opts.uploadMethod,
                element,
                targetHistoryId: opts.targetHistoryId,
                fileData: file,
                name: file.name,
                size: file.size,
            };
            const id = uploadState.addUploadItem(item);
            ids.push(id);
        });
        enqueueAll(ids);
        return ids;
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
        const item: NewUploadItem = {
            uploadMethod: opts.uploadMethod,
            element,
            targetHistoryId: opts.targetHistoryId,
            name: String(element.name ?? "Pasted content"),
            size: typeof content === "string" ? new Blob([content]).size : 0,
        };
        const id = uploadState.addUploadItem(item);
        enqueue(id);
        return id;
    }

    function enqueueUrls(urls: string[], opts: EnqueueOptions) {
        const ids: string[] = [];
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
                const item: NewUploadItem = {
                    uploadMethod: opts.uploadMethod,
                    element,
                    targetHistoryId: opts.targetHistoryId,
                    name: url,
                    size: 0,
                };
                const id = uploadState.addUploadItem(item);
                ids.push(id);
            });
        enqueueAll(ids);
        return ids;
    }

    function clearCompleted() {
        uploadState.clearCompleted();
    }

    function clearAll() {
        uploadState.clearAll();
    }

    return {
        // Low-level queue methods
        enqueue,
        enqueueAll,
        // High-level methods (recommended)
        enqueueLocalFiles,
        enqueuePastedContent,
        enqueueUrls,
        // Cleanup
        clearCompleted,
        clearAll,
        // Access to state for UI
        state: uploadState,
    };
}
