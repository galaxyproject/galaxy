import { bulkUpdate } from "./queries";

/**
 * Content operations
 */

export function hideSelectedContent(history, filters, items) {
    return bulkUpdate(history, "hide", filters, items);
}

export function unhideSelectedContent(history, filters, items) {
    return bulkUpdate(history, "unhide", filters, items);
}

export function deleteSelectedContent(history, filters, items) {
    return bulkUpdate(history, "delete", filters, items);
}

export function undeleteSelectedContent(history, filters, items) {
    return bulkUpdate(history, "undelete", filters, items);
}

export function purgeSelectedContent(history, filters, items) {
    return bulkUpdate(history, "purge", filters, items);
}

export function unhideAllHiddenContent(history) {
    const filters = { visible: false };
    return unhideSelectedContent(history, filters);
}

export function deleteAllHiddenContent(history) {
    const filters = { deleted: false, visible: false };
    return deleteSelectedContent(history, filters);
}

export function purgeAllDeletedContent(history) {
    const filters = { deleted: true };
    return purgeSelectedContent(history, filters);
}
