/**
 * Monitors and requests the summary of recently changed history items and commits the
 * results to the history items and other attached stores. The initial update time threshold
 * corresponds to the module import time. Once the start action is called, continuous requests
 * are submitted while the threshold is being increased by the throttle period and the request
 * response time for every consecutive request.
 */
import { urlData } from "utils/url";

let fetching = false;
let lastDate = new Date();
const limit = 100;
const throttlePeriod = 3000;

const actions = {
    fetchHistoryChangedItems: async ({ commit, dispatch }, { historyId }) => {
        const params = `limit=${limit}&q=update_time-ge&qv=${encodeURIComponent(lastDate.toISOString())}`;
        const url = `api/histories/${historyId}/contents?v=dev&view=detailed&${params}`;
        lastDate = new Date();
        const payload = await urlData({ url });
        if (payload && payload.length == limit) {
            console.debug(`Reached limit of monitored changes (limit=${limit}).`);
        }
        // passes changed items to attached stores
        commit("saveDatasets", { payload });
        commit("saveHistoryItems", { historyId, payload });
        commit("saveCollectionObjects", { payload });
        if (fetching) {
            setTimeout(() => {
                dispatch("fetchHistoryChangedItems", { historyId });
            }, throttlePeriod);
        }
    },
    startHistoryChangedItems: ({ dispatch }, { historyId }) => {
        if (!fetching) {
            fetching = true;
            dispatch("fetchHistoryChangedItems", { historyId });
        }
    },
    stopHistoryChangedItems: () => {
        fetching = false;
    },
};

export const historyChangedItemsStore = {
    actions,
};
