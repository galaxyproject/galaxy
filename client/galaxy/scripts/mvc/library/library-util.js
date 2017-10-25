define([], function() {
    /**
     * Create alphabetical based two-argument comparator
     * that takes into account that Folder > Dataset
     * @param  {str} sort_key   key to sort by
     * @param  {str} sort_order order to sort by (asc, desc)
     * @return {function} two-argument comparator function
     */
    var generateFolderComparator = function(sort_key, sort_order) {
        return function(itemA, itemB) {
            if (itemA.get("type") === itemB.get("type")) {
                if(sort_key === "file_ext"){
                    var a_has = itemA.hasOwnProperty("file_ext") && itemA.get("file_ext");
                    var b_has = itemB.hasOwnProperty("file_ext") && itemB.get("file_ext");
                    if (!(a_has && b_has)){
                        if (a_has && !b_has){
                            return -1;
                        }
                        if (!a_has && b_has){
                            return 1;
                        }
                        return 0;
                    }
                }
                if (
                    itemA.get(sort_key).toLowerCase() >
                    itemB.get(sort_key).toLowerCase()
                ) {
                    return sort_order === "asc" ? 1 : -1;
                }
                if (
                    itemB.get(sort_key).toLowerCase() >
                    itemA.get(sort_key).toLowerCase()
                ) {
                    return sort_order === "asc" ? -1 : 1;
                }
                return 0; // equal
            } else {
                if (itemA.get("type") === "folder") {
                    return -1; // folder is always before dataset
                } else {
                    return 1;
                }
            }
        };
    };
    /**
     * Create alphabetical based two-argument comparator
     * @param  {str} sort_key   key to sort by
     * @param  {str} sort_order order to sort by (asc, desc)
     * @return {function} two-argument comparator function
     */
    var generateLibraryComparator = function(sort_key, sort_order) {
        return function(libraryA, libraryB) {
            if (
                libraryA.get(sort_key).toLowerCase() >
                libraryB.get(sort_key).toLowerCase()
            ) {
                return sort_order === "asc" ? 1 : -1;
            }
            if (
                libraryB.get(sort_key).toLowerCase() >
                libraryA.get(sort_key).toLowerCase()
            ) {
                return sort_order === "asc" ? -1 : 1;
            }
            return 0; // equal
        };
    };
    return {
        generateFolderComparator: generateFolderComparator,
        generateLibraryComparator: generateLibraryComparator
    };
});
