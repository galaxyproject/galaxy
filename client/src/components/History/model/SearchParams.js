import config from "config";
import deepEqual from "deep-equal";

const pairSplitRE = /(\w+=\w+)|(\w+="(\w|\s)+")/g;
const scrubFieldRE = /[^\w]/g;
const scrubQuotesRE = /'|"/g;
const scrubSpaceRE = /\s+/g;

// Fields thata can be used for text searches
const validTextFields = new Set([
    "name",
    "history_content_type",
    "file_ext",
    "extension",
    "misc_info",
    "state",
    "hid",
    "tag",
]);

export class SearchParams {
    constructor(props = {}) {
        this.filterText = "";
        this.showDeleted = false;
        this.showHidden = false;
        Object.assign(this, props);
    }

    get pageSize() {
        return SearchParams.pageSize;
    }

    clone() {
        return new SearchParams(this);
    }

    // need this because of what Vue does to objects to make them reactive
    export() {
        const { filterText, showDeleted, showHidden } = this;
        return { filterText, showDeleted, showHidden };
    }

    // Filtering, turns field=val into an object we can use to build selectors
    parseTextFilter() {
        const raw = this.filterText;

        const result = new Map();
        if (!raw.length) return result;

        let matches = raw.match(pairSplitRE);
        if (matches === null && raw.length) matches = [`name=${raw}`];

        return matches.reduce((result, pair) => {
            const [field, val] = pair.split("=");
            const cleanField = field.replace(scrubFieldRE, "");

            if (validTextFields.has(cleanField)) {
                const cleanVal = val.replace(scrubQuotesRE, "").replace(scrubSpaceRE, " ");
                result.set(cleanField, cleanVal);
            }

            return result;
        }, result);
    }

    // output current state to log
    report(label = "params") {
        const { showDeleted, showHidden, filterText } = this;
        const dString = showDeleted ? "showDeleted" : "";
        const hString = showHidden ? "showHidden" : "";

        console.groupCollapsed(label, `(${dString} ${hString}`);
        console.log("showDeleted", showDeleted);
        console.log("showHidden", showHidden);
        console.log("filterText", filterText);
        console.groupEnd();
    }
}

// Statics

SearchParams.pageSize = config.caching.pageSize;

SearchParams.equals = function (a, b) {
    return deepEqual(a.export(), b.export());
};
