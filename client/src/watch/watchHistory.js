/**
 * Monitors and requests the summary of recently changed history items and commits the
 * results to the history items and other attached stores. The initial update time threshold
 * corresponds to the module import time. Once the watcher is called, continuous requests are
 * submitted, delayed only by the throttle period and the request response time.
 */

import { storeToRefs } from "pinia";
import { useHistoryItemsStore } from "stores/historyItemsStore";
import { useHistoryStore } from "stores/historyStore";
import { loadSet } from "utils/setCache";
import { urlData } from "utils/url";

import { useResourceWatcher } from "@/composables/resourceWatcher";
import { useCollectionElementsStore } from "@/stores/collectionElementsStore";
import { useDatasetStore } from "@/stores/datasetStore";

const limit = 1000;

export const ACTIVE_POLLING_INTERVAL = 3000;
export const INACTIVE_POLLING_INTERVAL = 60000;

// last time the history has changed
let lastUpdateTime = null;

// last time changed history items have been requested
let lastRequestDate = new Date();

const { startWatchingResource: startWatchingHistory } = useResourceWatcher(watchHistory, {
    shortPollingInterval: ACTIVE_POLLING_INTERVAL,
    longPollingInterval: INACTIVE_POLLING_INTERVAL,
});

export { startWatchingHistory };

export async function watchHistory(app) {
    // GalaxyApp
    const { isWatching } = storeToRefs(useHistoryItemsStore());
    try {
        isWatching.value = true;
        await watchHistoryOnce(app);
    } catch (error) {
        // error alerting the user that watch history failed
        console.warn(error);
        isWatching.value = false;
    }
}

export async function watchHistoryOnce(app) {
    const historyStore = useHistoryStore();
    const historyItemsStore = useHistoryItemsStore();
    const datasetStore = useDatasetStore();
    const collectionElementsStore = useCollectionElementsStore();

    // get current history
    const checkForUpdate = new Date();
    const history = await historyStore.loadCurrentHistory(lastUpdateTime);
    const { lastCheckedTime } = storeToRefs(historyItemsStore);
    lastCheckedTime.value = checkForUpdate;
    if (!history || !history.id) {
        return;
    }

    // continue if the history update time has changed
    if (!lastUpdateTime || lastUpdateTime < history.update_time) {
        const historyId = history.id;
        lastUpdateTime = history.update_time;
        historyItemsStore.setLastUpdateTime();
        // execute request to obtain recently changed items
        const params = {
            v: "dev",
            limit: limit,
            q: "update_time-ge",
            qv: lastRequestDate.toISOString(),
        };
        // request detailed info only for the expanded datasets
        const detailedIds = getCurrentlyExpandedHistoryContentIds();
        if (detailedIds.length) {
            params["details"] = detailedIds.join(",");
        }
        const url = `/api/histories/${historyId}/contents`;
        lastRequestDate = new Date();
        const payload = await urlData({ url, params });
        // show warning that not all changes have been obtained
        if (payload && payload.length == limit) {
            console.debug(`Reached limit of monitored changes (limit=${limit}).`);
        }
        // pass changed items to attached stores
        historyStore.setHistory(history);
        datasetStore.saveDatasets(payload);
        historyItemsStore.saveHistoryItems(historyId, payload);
        collectionElementsStore.saveCollections(payload);
        // trigger changes in legacy handler
        if (app) {
            app.user.fetch({
                url: `${app.user.urlRoot()}/${app.user.id || "current"}`,
            });
        }
    }
}

/**
 * Returns the set of history item IDs that are currently expanded in the history panel from the cache.
 * These content items need to retrieve detailed information when updated.
 * @returns {Array<string>} List of history item IDs that are currently expanded.
 */
function getCurrentlyExpandedHistoryContentIds() {
    const expandedItemIds = [];
    const cacheKey = "expanded-history-items";
    const expandedItems = loadSet(cacheKey);
    expandedItems.forEach((key) => {
        // Items have the format: <type>-<id>
        const itemId = key.split("-")[1];
        if (itemId?.trim()) {
            expandedItemIds.push(itemId);
        }
    });
    return expandedItemIds;
}
