/**
 * Requests history items by reacting to changes of filter props passed
 * to the history items provider used in the history panel.
 */

import { reverse } from "lodash";
import { LastQueue } from "utils/promise-queue";
import { urlData } from "utils/url";
import { getFilterDict, mergeArray } from "./utilities";

const limit = 100;
const queue = new LastQueue();

const state = {
    items: {},
    itemKey: "hid",
};

const getters = {
    getHistoryItems:
        (state) =>
        ({ historyId, filterText, showDeleted, showHidden }) => {
            const itemArray = state.items[historyId] || [];
            const filtered = itemArray.filter((item) => {
                if (!item) {
                    return false;
                }
                if (showDeleted != item.deleted) {
                    return false;
                }
                if (showHidden == item.visible) {
                    return false;
                }
                const filterDict = getFilterDict(filterText);
                for (const [key, value] of Object.entries(filterDict)) {
                    const itemValue = String(item[key]);
                    if (!itemValue.includes(value)) {
                        return false;
                    }
                }
                return true;
            });
            return reverse(filtered);
        },
};

const getQueryString = (filterText, showDeleted, showHidden) => {
    const deleted = showDeleted ? "True" : "False";
    const visible = showHidden ? "False" : "True";
    return `q=deleted&q=visible&qv=${deleted}&qv=${visible}`;
};

const actions = {
    fetchHistoryItems: async ({ commit, dispatch }, { historyId, offset, filterText, showDeleted, showHidden }) => {
        dispatch("startHistoryChangedItems", { historyId: historyId });
        const queryString = getQueryString(filterText, showDeleted, showHidden);
        const params = `v=dev&order=hid&offset=${offset}&limit=${limit}`;
        const url = `api/histories/${historyId}/contents?${params}&${queryString}`;
        await queue.enqueue(urlData, { url }).then((payload) => {
            commit("saveHistoryItems", { historyId, payload });
        });
    },
};

const mutations = {
    saveHistoryItems: (state, { historyId, payload }) => {
        mergeArray(historyId, payload, state.items, state.itemKey);
    },
};

export const historyItemsStore = {
    state,
    getters,
    actions,
    mutations,
};
