import Vue from "vue";

/* This function merges the existing data with new incoming data. */
export function mergeListing(state, { payload, newQueryKey = null }) {
    state.itemQueryKey = state.itemQueryKey || newQueryKey;
    if (newQueryKey && state.itemQueryKey != newQueryKey) {
        state.itemQueryKey = newQueryKey;
        state.items.splice(0);
    }
    for (const item of payload) {
        const itemIndex = item[state.itemKey];
        if (state.items[itemIndex]) {
            const localItem = state.items[itemIndex];
            Object.keys(localItem).forEach((key) => {
                localItem[key] = item[key];
            });
        } else {
            Vue.set(state.items, itemIndex, item);
        }
    }
}
