import Vue from "vue";

export function mergeListing(state, { queryKey, payload }) {
    /* This function merges the existing data with new incoming data. */
    state.queryCurrent = state.queryCurrent || queryKey;
    if (queryKey != state.queryCurrent) {
        state.queryCurrent = queryKey;
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
