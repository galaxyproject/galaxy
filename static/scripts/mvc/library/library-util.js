define("mvc/library/library-util", ["exports"], function(exports) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });
    /**
     * Create alphabetical based two-argument comparator
     * that takes into account that Folder comes before Dataset.
     * If sort_key is not present it is set to ''.
     * @param  {str} sort_key   key to sort by
     * @param  {str} sort_order order to sort by (asc, desc)
     * @return {function} two-argument comparator function
     */
    var generateFolderComparator = function generateFolderComparator(sort_key, sort_order) {
        return function(itemA, itemB) {
            if (itemA.get("type") === itemB.get("type")) {
                if (!itemA.has(sort_key) && !itemB.has(sort_key)) {
                    return 0;
                } else if (!itemA.has(sort_key)) {
                    return 1;
                } else if (!itemB.has(sort_key)) {
                    return -1;
                }
                if (itemA.get(sort_key).toLowerCase() > itemB.get(sort_key).toLowerCase()) {
                    return sort_order === "asc" ? 1 : -1;
                }
                if (itemB.get(sort_key).toLowerCase() > itemA.get(sort_key).toLowerCase()) {
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
    };
    /**
     * Create alphabetical based two-argument comparator
     * @param  {str} sort_key   key to sort by
     * @param  {str} sort_order order to sort by (asc, desc)
     * @return {function} two-argument comparator function
     */
    var generateLibraryComparator = function generateLibraryComparator(sort_key, sort_order) {
        return function(libraryA, libraryB) {
            if (libraryA.get(sort_key).toLowerCase() > libraryB.get(sort_key).toLowerCase()) {
                return sort_order === "asc" ? 1 : -1;
            }
            if (libraryB.get(sort_key).toLowerCase() > libraryA.get(sort_key).toLowerCase()) {
                return sort_order === "asc" ? -1 : 1;
            }
            return 0; // equal
        };
    };
    exports.default = {
        generateFolderComparator: generateFolderComparator,
        generateLibraryComparator: generateLibraryComparator
    };
});
//# sourceMappingURL=../../../maps/mvc/library/library-util.js.map
