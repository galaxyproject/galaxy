import { set } from "vue";

/* This function merges the existing data with new incoming data. */
export function mergeArray(id, payload, items, itemKey) {
    if (!items[id]) {
        set(items, id, []);
    }
    const itemArray = items[id];
    for (const item of payload) {
        const itemIndex = item[itemKey];
        if (itemArray[itemIndex]) {
            const localItem = itemArray[itemIndex];
            if (localItem.id == item.id) {
                Object.keys(localItem).forEach((key) => {
                    // Maybe it's ok to overwrite the `sub_items` key here because that
                    // array might contain items not returned for current filter?
                    if (key !== "sub_items") {
                        localItem[key] = item[key];
                    }
                });
            }
            // the `item.id` is different with the same `hid`,
            // so we add a key `sub_items` to this item and add any other related item(s) to it
            else {
                // But first, we check a few conditions and based on those, possibly replace the `localItem` with the new item
                if (
                    // 1: `localItem` is not in the `payload` (for filter)
                    new Date(item.create_time) < new Date(localItem.create_time) ||
                    // 2: `localItem` has fewer keys than the new item
                    Object.keys(localItem).length < Object.keys(item).length
                ) {
                    set(itemArray, itemIndex, item);
                    pushSubItem(item, localItem);
                    localItem.sub_items = [];
                } else {
                    pushSubItem(localItem, item);
                }
            }
        } else {
            set(itemArray, itemIndex, item);
        }
    }
}

function pushSubItem(item, subItem) {
    if (!item.sub_items) {
        item["sub_items"] = [];
    }
    if (!item["sub_items"].find((i) => i.id === subItem.id)) {
        item["sub_items"].push(subItem);
    }
}
