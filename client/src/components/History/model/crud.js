import { bulkUpdate, getAllContentByFilter } from "./queries";

/**
 * Content operations
 */

export async function hideSelectedContent(history, type_ids, filterParams) {
    return await bulkUpdate(history, "hide", type_ids, filterParams);
}

export async function unhideSelectedContent(history, type_ids, filterParams) {
    return await bulkUpdate(history, "unhide", type_ids, filterParams);
}

export async function deleteSelectedContent(history, type_ids, filterParams) {
    return await bulkUpdate(history, "delete", type_ids, filterParams);
}

export async function undeleteSelectedContent(history, type_ids, filterParams) {
    return await bulkUpdate(history, "undelete", type_ids, filterParams);
}

export async function purgeSelectedContent(history, type_ids, filterParams) {
    return await bulkUpdate(history, "purge", type_ids, filterParams);
}

export async function unhideAllHiddenContent(history) {
    const filter = { visible: false };
    const selection = await getAllContentByFilter(history, filter);
    if (selection.length) {
        const type_ids = selection.map((c) => c.type_id);
        return await unhideSelectedContent(history, type_ids);
    }
    return [];
}

export async function deleteAllHiddenContent(history) {
    const filter = { visible: false };
    const selection = await getAllContentByFilter(history, filter);
    if (selection.length) {
        const type_ids = selection.map((c) => c.type_id);
        return await deleteSelectedContent(history, type_ids);
    }
    return [];
}

export async function purgeAllDeletedContent(history) {
    const filter = { deleted: true, purged: false };
    const selection = await getAllContentByFilter(history, filter);
    if (selection.length) {
        const type_ids = selection.map((c) => c.type_id);
        return await purgeSelectedContent(history, type_ids);
    }
    return [];
}
