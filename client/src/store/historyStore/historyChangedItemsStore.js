import { urlData } from "utils/url";

let fetching = false;
const throttlePeriod = 1000;

const actions = {
    fetchHistoryChangedItems: async ({ commit, dispatch }, { historyId }) => {
        const url = `api/histories/${historyId}/contents?v=dev`;
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
