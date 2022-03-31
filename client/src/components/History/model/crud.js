import { bulkUpdate } from "./queries";

/**
 * Content operations
 */

export async function hideSelectedContent(history, filters, items) {
    return await bulkUpdate(history, "hide", filters, items);
}

export async function unhideSelectedContent(history, filters, items) {
    return await bulkUpdate(history, "unhide", filters, items);
}

export async function deleteSelectedContent(history, filters, items) {
    return await bulkUpdate(history, "delete", filters, items);
}

export async function undeleteSelectedContent(history, filters, items) {
    return await bulkUpdate(history, "undelete", filters, items);
}

export async function purgeSelectedContent(history, filters, items) {
    return await bulkUpdate(history, "purge", filters, items);
}

export async function unhideAllHiddenContent(history) {
    const filters = [["visible", false]];
    return await unhideSelectedContent(history, filters);
}

export async function deleteAllHiddenContent(history) {
    const filters = [
        ["deleted", false],
        ["visible", false],
    ];
    return await deleteSelectedContent(history, filters);
}

export async function purgeAllDeletedContent(history) {
    const filters = [["deleted", true]];
    return await purgeSelectedContent(history, filters);
}
