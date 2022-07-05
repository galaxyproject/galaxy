/**
 * Monitors and requests the summary of recently changed history items and commits the
 * results to the history items and other attached stores. The initial update time threshold
 * corresponds to the module import time. Once the watcher is called, continuous requests are
 * submitted, delayed only by the throttle period and the request response time.
 */

import defaultStore from "store/index";
import { urlData } from "utils/url";
import { getCurrentHistoryFromServer } from "./queries";
import { getGalaxyInstance } from "app";

const limit = 1000;

let throttlePeriod = 3000;
let watchTimeout = null;

// last time the history has changed
let lastUpdateTime = null;

// last time changed history items have been requested
let lastRequestDate = new Date();

// We only want to kick this off once we're actively watching history
let watchingVisibility = false;

function setVisibilityThrottle() {
    if (document.visibilityState === "visible") {
        // Poll every 3 seconds when visible
        throttlePeriod = 3000;
        rewatchHistory();
    } else {
        // Poll every 60 seconds when hidden/backgrounded
        throttlePeriod = 60000;
    }
}

export async function watchHistoryOnce(store) {
    // "Reset" watchTimeout so we don't queue up watchHistory calls in rewatchHistory.
    watchTimeout = null;
    // get current history
    const checkForUpdate = new Date();
    const history = await getCurrentHistoryFromServer(lastUpdateTime);
    store.commit("setLastCheckedTime", { checkForUpdate });
    if (!history) {
        return;
    }

    // continue if the history update time has changed
    if (!lastUpdateTime || lastUpdateTime < history.update_time) {
        const historyId = history.id;
        lastUpdateTime = history.update_time;
        // execute request to obtain recently changed items
        const params = {
            limit: limit,
            q: "update_time-ge",
            qv: lastRequestDate.toISOString(),
            v: "dev",
            view: "detailed",
        };
        const paramsString = Object.entries(params)
            .map(([k, v]) => `${k}=${encodeURIComponent(v)}`)
            .join("&");
        const url = `api/histories/${historyId}/contents?${paramsString}`;
        lastRequestDate = new Date();
        const payload = await urlData({ url });
        // show warning that not all changes have been obtained
        if (payload && payload.length == limit) {
            console.debug(`Reached limit of monitored changes (limit=${limit}).`);
        }
        // pass changed items to attached stores
        store.commit("history/setHistory", history);
        store.commit("saveDatasets", { payload });
        store.commit("saveHistoryItems", { historyId, payload });
        store.commit("saveCollectionObjects", { payload });
        // trigger changes in legacy handler
        const Galaxy = getGalaxyInstance();
        if (Galaxy) {
            Galaxy.user.fetch({
                url: `${Galaxy.user.urlRoot()}/${Galaxy.user.id || "current"}`,
            });
        }
    }
}

export async function watchHistory(store = defaultStore) {
    // Only set up visibility listeners once, whenever a watch is first started
    if (watchingVisibility === false) {
        watchingVisibility = true;
        document.addEventListener("visibilitychange", setVisibilityThrottle);
    }
    try {
        await watchHistoryOnce(store);
    } catch (error) {
        // would be fantastic if we could show some error alerting the user to this
        console.warn(error);
    } finally {
        watchTimeout = setTimeout(() => {
            watchHistory(store);
        }, throttlePeriod);
    }
}

export function rewatchHistory() {
    if (watchTimeout) {
        clearTimeout(watchTimeout);
        watchHistory();
    }
}
