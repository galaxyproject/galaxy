/** Returns true if the item is a dataset entry **/
export function isDataset(item) {
    return item.history_content_type == "dataset" || item.type == "file";
}

export class UrlTracker {
    constructor(rootUrl) {
        this.rootUrl = rootUrl;
        this.navigation = [];
    }

    /** Returns and tracks urls for data drilling **/
    getUrl(url) {
        if (url) {
            this.navigation.push(url);
        } else {
            this.navigation.pop();
            let navigationLength = this.navigation.length;
            if (navigationLength > 0) {
                url = this.navigation[navigationLength - 1];
            } else {
                url = this.rootUrl;
            }
        }
        return url;
    }
}
