/** Returns true if the item is a dataset entry **/
export function isDataset(item) {
    return item.history_content_type == "dataset" || item.type == "file";
}
