import { bulkCacheContent } from "components/providers/History/caching";
import { bulkContentUpdate, getAllContentByFilter } from "./queries";

/**
 * Content crud operations, usually an ajax call + a cache function
 */

export const updateSelectedContent = (updates) => async (history, type_ids) => {
    // single ajax call with wierd syntax because.... reasons
    const changes = await bulkContentUpdate(history, type_ids, updates);
    const cacheResult = await bulkCacheContent(changes, true);
    console.log("cacheResult", changes, cacheResult);
    return cacheResult;
};

export const hideSelectedContent = updateSelectedContent({
    visible: false,
});

export const unhideSelectedContent = updateSelectedContent({
    visible: true,
});

export const deleteSelectedContent = updateSelectedContent({
    deleted: true,
});

export const undeleteSelectedContent = updateSelectedContent({
    deleted: false,
});

export const purgeSelectedContent = updateSelectedContent({
    deleted: true,
    purged: true,
});

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
