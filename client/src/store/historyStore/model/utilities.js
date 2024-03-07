import Vue from "vue";

/* This function merges the existing data with new incoming data. */
export function mergeArray(id, payload, items, itemKey, nonKeyedValues = {}) {
    if (!items[id]) {
        Vue.set(items, id, []);
    }
    const itemArray = items[id];
    for (const item of payload) {
        const itemIndex = item[itemKey];
        if (itemArray[itemIndex]) {
            const localItem = itemArray[itemIndex];
            if (localItem.id == item.id) {
                Object.keys(localItem).forEach((key) => {
                    localItem[key] = item[key];
                });

                // for each non-keyed value, create a new key in the local item
                Object.keys(nonKeyedValues).forEach((key) => {
                    Vue.set(localItem, key, nonKeyedValues[key]);
                });
            }
        } else {
            Vue.set(itemArray, itemIndex, item);
            const localItem = itemArray[itemIndex];
            // for each non-keyed value, create a new key in the local item
            Object.keys(nonKeyedValues).forEach((key) => {
                Vue.set(localItem, key, nonKeyedValues[key]);
            });
        }
    }
}
