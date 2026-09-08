/**
 * Cancellation registry for in-progress uploads.
 *
 * Maintains module-level maps of `AbortController` instances keyed by
 * upload item ID and batch ID so that any component can cancel an
 * upload or batch without holding a direct reference to the controller.
 *
 * Standalone items each get their own controller, so cancelling one item
 * doesn't affect the others. Collection batches are submitted atomically,
 * so every item in a batch shares the batch's single controller — cancelling
 * any one item (or the batch itself) cancels the whole batch.
 */

/** Map of upload item ID → AbortController */
const uploadControllers = new Map<string, AbortController>();

/** Map of batch ID → AbortController */
const batchControllers = new Map<string, AbortController>();

/**
 * Registers an `AbortController` for a set of upload items and optionally a batch.
 *
 * @param uploadIds - Upload item IDs that share this controller
 * @param batchId - Optional batch ID that shares this controller
 * @param controller - The `AbortController` to register
 */
export function registerUploadController(
    uploadIds: string[],
    batchId: string | undefined,
    controller: AbortController,
): void {
    for (const id of uploadIds) {
        uploadControllers.set(id, controller);
    }
    if (batchId) {
        batchControllers.set(batchId, controller);
    }
}

/**
 * Removes all registrations for the given upload IDs and batch.
 *
 * @param uploadIds - Upload item IDs to unregister
 * @param batchId - Optional batch ID to unregister
 */
export function unregisterUploadController(uploadIds: string[], batchId: string | undefined): void {
    for (const id of uploadIds) {
        uploadControllers.delete(id);
    }
    if (batchId) {
        batchControllers.delete(batchId);
    }
}

/**
 * Cancels a single upload item by aborting its registered controller.
 * Has no effect if the item is not registered or already aborted.
 *
 * @param uploadId - The upload item ID to cancel
 */
export function abortUploadController(uploadId: string): void {
    const controller = uploadControllers.get(uploadId);
    if (controller && !controller.signal.aborted) {
        controller.abort();
    }
}

/**
 * Cancels an entire batch by aborting its registered controller.
 * Has no effect if the batch is not registered or already aborted.
 *
 * @param batchId - The batch ID to cancel
 */
export function abortBatchController(batchId: string): void {
    const controller = batchControllers.get(batchId);
    if (controller && !controller.signal.aborted) {
        controller.abort();
    }
}

/**
 * Cancels all active uploads by aborting every registered controller.
 * Uses a `Set` to avoid calling `.abort()` twice on shared controllers.
 */
export function abortAllUploadControllers(): void {
    const seen = new Set<AbortController>();
    for (const controller of uploadControllers.values()) {
        seen.add(controller);
    }
    for (const controller of batchControllers.values()) {
        seen.add(controller);
    }
    for (const controller of seen) {
        if (!controller.signal.aborted) {
            controller.abort();
        }
    }
}
