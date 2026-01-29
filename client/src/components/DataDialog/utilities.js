/** This helps track urls for data drilling **/
export class UrlTracker {
    constructor(root) {
        this.root = root;
        this.navigation = [];
    }

    /** Returns urls for data drilling **/
    getUrl(url, returnWithPrevious = false) {
        let previous = undefined;
        if (url) {
            this.navigation.push(url);
        } else {
            previous = this.navigation.pop();
            const navigationLength = this.navigation.length;
            if (navigationLength > 0) {
                url = this.navigation[navigationLength - 1];
            } else {
                url = this.root;
            }
        }

        if (returnWithPrevious) {
            return { url, popped: previous };
        } else {
            return url;
        }
    }

    /** Returns true if the last data is at navigation root **/
    atRoot() {
        return this.navigation.length == 0;
    }
}
