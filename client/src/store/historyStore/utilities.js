import Vue from "vue";

/* This function merges the existing data with new incoming data. */
export function mergeArray(id, payload, items, itemKey) {
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
            }
        } else {
            Vue.set(itemArray, itemIndex, item);
        }
    }
}

/* Parses single text input into a dict of field->value pairs. */
export function getFilterDict(filterText, validFields) {
    const pairSplitRE = /(\w+=\w+)|(\w+="(\w|\s)+")/g;
    const scrubQuotesRE = /'|"/g;
    const result = {};
    if (filterText.length == 0) {
        return result;
    }
    let matches = filterText.match(pairSplitRE);
    if (!matches && filterText.length > 0 && !filterText.includes("=")) {
        matches = [`name=${filterText}`];
    }
    if (matches) {
        matches.forEach((pair) => {
            const [field, value] = pair.split("=");
            if (validFields.has(field)) {
                result[field] = value.replace(scrubQuotesRE, "");
            }
        });
    }
    return result;
}
