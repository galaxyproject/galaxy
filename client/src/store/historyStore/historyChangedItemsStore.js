import { urlData } from "utils/url";

let fetching = false;
let lastDate = new Date();
const throttlePeriod = 3000;

const actions = {
    fetchHistoryChangedItems: async ({ commit, dispatch }, { historyId }) => {
        const params = `q=update_time-ge&qv=${lastDate.toISOString()}`;
        const url = `api/histories/${historyId}/contents?v=dev&${params}`;
        const payload = await urlData({ url });
        // TODO: Might be more accurate to instead identify the update time of the last entry received.
        lastDate = new Date();
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
