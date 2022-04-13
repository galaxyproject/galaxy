/**
 * Monitors and requests the summary of recently changed history items and commits the
 * results to the history items and other attached stores. The initial update time threshold
 * corresponds to the module import time. Once the watcher is called, continuous requests are
 * submitted, delayed only by the throttle period and the request response time.
 */

import store from "store";
import { urlData } from "utils/url";
import { getCurrentHistoryFromServer } from "./queries";
import { getGalaxyInstance } from "app";

const limit = 1000;
const throttlePeriod = 3000;

// last time the history has been requests
let lastUpdateTime = null;
let lastRequestDate = new Date();

export function watchHistory() {
    // get current history
    getCurrentHistoryFromServer().then((history) => {
        const historyId = history.id;
        lastUpdateTime = lastUpdateTime || history.update_time;
        // continue if the history update time has changed
        if (lastUpdateTime != history.update_time) {
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
            urlData({ url }).then((payload) => {
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
                Galaxy.user.fetch({
                    url: `${Galaxy.user.urlRoot()}/${Galaxy.user.id || "current"}`,
                });
            });
        }
        setTimeout(() => {
            watchHistory(store);
        }, throttlePeriod);
    });
}
