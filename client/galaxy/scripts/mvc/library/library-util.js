/**
 * Create alphabetical based two-argument comparator
 * that takes into account that Folder comes before Dataset.
 * If sort_key is not present it is set to ''.
 * @param  {str} sort_key   key to sort by
 * @param  {str} sort_order order to sort by (asc, desc)
 * @return {function} two-argument comparator function
 */
var generateComparator = (sort_key, sort_order) => (itemA, itemB) => {
    if (itemA.get("type") === itemB.get("type")) {
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
        }
        else
        {
            comparable_itemA_key = itemA.get(sort_key).toLowerCase();
            comparable_itemB_key = itemB.get(sort_key).toLowerCase();
        }
        if ( comparable_itemA_key > comparable_itemB_key) {
            return sort_order === "asc" ? 1 : -1;
        }
        if (comparable_itemB_key > comparable_itemA_key) {
            return sort_order === "asc" ? -1 : 1;
        }
        
        return 0; // equal
    } else {
        if (itemA.get("type") === "folder") {
            return -1; // folder is always before dataset
        }
        return 1;
    }
};
export default {
    generateComparator: generateComparator
};
