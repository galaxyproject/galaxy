import { set } from "vue";

// TODO: This is a temporary solution to handle compressed files. We need to find a better way to handle this.
const COMPRESSED_EXTENSIONS = ["tabix", "tar.gz", "zip", "tar.bz2", "fa.gz", "fa.bz2", "_bgzip"];

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
                    !payload.find((p) => p.id === localItem.id) ||
                    // 2: `localItem` is compressed and the new `item` is not
                    (localItem.extension &&
                        item.extension &&
                        COMPRESSED_EXTENSIONS.some((ext) => localItem.extension.includes(ext)) &&
                        !COMPRESSED_EXTENSIONS.some((ext) => item.extension.includes(ext)))
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
