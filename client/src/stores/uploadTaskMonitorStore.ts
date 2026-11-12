import { defineStore } from "pinia";
import { computed, type EffectScope, effectScope, onScopeDispose, watch } from "vue";

import { useUploadState } from "@/components/Panels/Upload/uploadState";
import { useTaskMonitor } from "@/composables/taskMonitor";
import type { GalaxyLinkUploadItem, UploadItem } from "@/composables/upload/uploadItemTypes";

const POLL_DELAY = 3000;
// A short network problem should not fail an import that keeps running on the server.
const MAX_STATUS_FAILURES = 3;
// Imports this page starts are created after this, so only an earlier page's can be left without a task.
const PAGE_LOADED_AT = Date.now();

export const COULD_NOT_IMPORT =
    "The link could not be imported. It may have expired, or the other Galaxy may not have finished preparing it.";
export const COULD_NOT_CHECK_IMPORT =
    "Galaxy could not check how the import is going. It may still finish, so look at the history.";
export const INTERRUPTED_IMPORT =
    "The page was left before Galaxy started the import. Look at the history first, then try again.";

// The scheme is optional: requests errors name only the path ("Max retries exceeded with url: /api/...").
const EXPORT_LINK = /(?:\b[a-z][a-z0-9+.-]*:\/\/)?[^\s'"<>]*short_term_storage\/[^\s'"<>]*/gi;

/**
 * Hides export links in a message before it is kept in upload state, which is stored in the browser:
 * anyone with such a link can download the item until it expires, and Galaxy errors may repeat the link.
 */
export function redactExportLinks(message: string, link?: string) {
    const withoutLink = link ? message.split(link).join("[export link]") : message;
    return withoutLink.replace(EXPORT_LINK, "[export link]");
}

function isTaskImport(item: UploadItem): item is GalaxyLinkUploadItem & UploadItem {
    return item.uploadMode === "galaxy-link";
}

/**
 * Follows the upload items that Galaxy imports in a background task, such as links from another Galaxy,
 * until their task ends. The task id is kept in upload state, so this picks them up again after a reload.
 */
export const useUploadTaskMonitorStore = defineStore("uploadTaskMonitor", () => {
    const uploadState = useUploadState();
    const followed = new Map<string, EffectScope>();

    // Waiting for a start request that an earlier page sent; the user's uploads may load from storage after this store.
    const interrupted = computed(() =>
        uploadState.activeItems.value.filter(
            (item) => isTaskImport(item) && item.status === "queued" && !item.taskId && item.createdAt < PAGE_LOADED_AT,
        ),
    );

    const running = computed(() =>
        uploadState.activeItems.value.flatMap((item) =>
            isTaskImport(item) && item.status === "processing" && item.taskId
                ? [{ uploadId: item.id, taskId: item.taskId, createdAt: item.createdAt }]
                : [],
        ),
    );

    function follow(uploadId: string, taskId: string, createdAt: number) {
        const scope = effectScope(true);
        scope.run(() => {
            const monitor = useTaskMonitor({ maxRequestFailures: MAX_STATUS_FAILURES });
            // Past this, Galaxy may have forgotten the task and report it as pending for good.
            const expiresIn = createdAt + (monitor.expirationTime ?? Infinity) - Date.now();
            if (expiresIn <= 0) {
                uploadState.setError(uploadId, COULD_NOT_CHECK_IMPORT);
                return;
            }
            const expiry = setTimeout(() => uploadState.setError(uploadId, COULD_NOT_CHECK_IMPORT), expiresIn);
            onScopeDispose(() => clearTimeout(expiry));
            watch(
                [monitor.isCompleted, monitor.hasFailed, monitor.failureReason, monitor.requestHasFailed],
                ([completed, failed, failureReason, requestFailed]) => {
                    if (completed) {
                        uploadState.markDatasetsResolved(uploadId);
                    } else if (failed && failureReason !== undefined) {
                        uploadState.setError(
                            uploadId,
                            redactExportLinks([COULD_NOT_IMPORT, failureReason].filter(Boolean).join(" ")),
                        );
                    } else if (requestFailed) {
                        uploadState.setError(uploadId, COULD_NOT_CHECK_IMPORT);
                    }
                },
            );
            monitor.waitForTask(taskId, POLL_DELAY);
        });
        followed.set(uploadId, scope);
    }

    watch(
        interrupted,
        (items) => {
            for (const item of items) {
                uploadState.setError(item.id, INTERRUPTED_IMPORT);
            }
        },
        { immediate: true },
    );

    watch(
        running,
        (entries) => {
            const ids = new Set(entries.map((entry) => entry.uploadId));
            followed.forEach((scope, uploadId) => {
                if (!ids.has(uploadId)) {
                    scope.stop();
                    followed.delete(uploadId);
                }
            });
            for (const { uploadId, taskId, createdAt } of entries) {
                if (!followed.has(uploadId)) {
                    follow(uploadId, taskId, createdAt);
                }
            }
        },
        { immediate: true },
    );

    onScopeDispose(() => {
        followed.forEach((scope) => scope.stop());
        followed.clear();
    });

    return {};
});
