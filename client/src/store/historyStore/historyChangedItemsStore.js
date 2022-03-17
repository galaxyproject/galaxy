/**
 * Monitors and requests the summary of recently changed history items and
 * commits the result to the history items store.
 */
import { urlData } from "utils/url";

let fetching = false;
let lastDate = new Date();
const limit = 100;
const throttlePeriod = 3000;

const actions = {
    fetchHistoryChangedItems: async ({ commit, dispatch }, { historyId }) => {
        const params = `limit=${limit}&q=update_time-ge&qv=${lastDate.toISOString()}`;
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
