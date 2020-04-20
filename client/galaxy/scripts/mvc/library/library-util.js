/**
 * Create alphabetical based two-argument comparator to handle library items (including folders)
 * If sort_key is not present it is set to ''.
 * @param  {str} sort_key   key to sort by
 * @param  {str} sort_order order to sort by (asc, desc)
 * @return {function} two-argument comparator function
 */
var generateComparator = (sort_key, sort_order) => (itemA, itemB) => {
    if (!itemA.has(sort_key) && !itemB.has(sort_key)) {
        return 0;
    } else if (!itemA.has(sort_key)) {
        return 1;
    } else if (!itemB.has(sort_key)) {
        return -1;
    }
    var comparable_itemA_key;
    var comparable_itemB_key;
    if (typeof itemA.get(sort_key) === "number") {
        comparable_itemA_key = itemA.get(sort_key);
        comparable_itemB_key = itemB.get(sort_key);
    } else {
        comparable_itemA_key = itemA.get(sort_key).toLowerCase();
        comparable_itemB_key = itemB.get(sort_key).toLowerCase();
    }

    if (comparable_itemA_key > comparable_itemB_key) {
        return sort_order === "asc" ? 1 : -1;
    }
    if (comparable_itemB_key > comparable_itemA_key) {
        return sort_order === "asc" ? -1 : 1;
    }

    return 0; // equal
};
export default {
    generateComparator: generateComparator,
};
