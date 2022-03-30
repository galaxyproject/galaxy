import { bulkUpdate } from "./queries";

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
    const type_ids = [];
    const filterParams = { filterText: "", showDeleted: false, showHidden: true };
    return await unhideSelectedContent(history, type_ids, filterParams);
}

export async function deleteAllHiddenContent(history) {
    const type_ids = [];
    const filterParams = { filterText: "", showDeleted: false, showHidden: true };
    return await deleteSelectedContent(history, type_ids, filterParams);
}

export async function purgeAllDeletedContent(history) {
    const type_ids = [];
    const filterParams = { filterText: "", showDeleted: true, showHidden: false };
    return await purgeSelectedContent(history, type_ids, filterParams);
}
