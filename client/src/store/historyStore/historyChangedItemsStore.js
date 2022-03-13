/**
 * Monitors and requests the summary of recently changed history items and
 * commits the result to the history items store.
 */
import { urlData } from "utils/url";

let fetching = false;
let lastDate = new Date();
const throttlePeriod = 3000;

const actions = {
    fetchHistoryChangedItems: async ({ commit, dispatch }, { historyId }) => {
        const params = `q=update_time-ge&qv=${lastDate.toISOString()}`;
        const url = `api/histories/${historyId}/contents?v=dev&${params}`;
        lastDate = new Date();
        const payload = await urlData({ url });
        commit("saveHistoryItems", { payload });
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
