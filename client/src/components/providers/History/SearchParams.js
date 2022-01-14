import deepEqual from "deep-equal";
import { isString } from "underscore";

const pairSplitRE = /(\w+=\w+)|(\w+="(\w|\s)+")/g;
const scrubFieldRE = /[^\w]/g;
const scrubQuotesRE = /'|"/g;

// Fields that can be used for text searches
const validTextFields = new Set([
    "name",
    "history_content_type",
    "type",
    "format",
    "extension",
    "misc_info",
    "state",
    "hid",
    "database",
    "annotation",
    "description",
    "tag",
    "tags",
]);

// alias search field to internal field (requestd name: pouch field name)
const pouchFieldAlias = {
    format: "file_ext",
    database: "genome_build",
    description: "annotation",
    tag: "tags",
    deleted: "isDeleted",
    type: "history_content_type",
};

// maps user-field -> server querystring field
// if maps to null, that filter not available on server
const serverFieldAlias = {
    tags: "tag",
    file_ext: null,
    genome_build: null,
};

// Convert actualy boolean into objectively incorrect python value our server accepts
const dumbBool = (val) => (val ? "True" : "False");

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

    // Filtering, parses single text input into a map of field->value
    // in the case of multiples, maps to field -> [value, value]
    get textCriteria() {
        const raw = this.filterText;

        const result = new Map();
        if (!raw.length) {
            return result;
        }

        let matches = raw.match(pairSplitRE);
        if (matches === null && raw.length) {
            matches = [`name=${raw}`];
        }

        const criteria = matches.reduce((result, pair) => {
            const [field, val] = pair.split("=");

            if (validTextFields.has(field)) {
                let cleanVal = val.replace(scrubQuotesRE, "");
                // set an array of criteria if we have multiples of the same field name
                if (result.has(field)) {
                    cleanVal = [result.get(field), cleanVal].flat();
                }

                result.set(field, cleanVal);
            }

            return result;
        }, result);

        return criteria;
    }

    // all criteria, map of field->value, includes our non-standard boolean filters
    get criteria() {
        const criteria = new Map(this.textCriteria);
        criteria.set("visible", !this.showHidden);
        criteria.set("deleted", this.showDeleted);
        return criteria;
    }

    // Generates an array of pouchDB selector objects
    // { field: { $operator: value }}
    get pouchFilters() {
        const filters = Array.from(this.criteria)
            // generate multiple objects for duplicated field=val entries
            // these will be AND-ed together in the final pouch selector
            // map userfield to pouchfield, userfield = what the user typed in the box
            // pouchfield = the actual field in the cache
            .map(([userField, val]) => [this.getPouchFieldName(userField), val])
            .map(([pouchField, val]) => {
                const vals = Array.isArray(val) ? val : [val];
                return vals.map((v) => [pouchField, v]);
            })
            .flat()
            .map(([pouchField, val]) => {
                const comparator = isString(val) ? { $regex: new RegExp(val) } : { $eq: val };
                return { [pouchField]: comparator };
            });

        return filters;
    }

    // Creates an object of query criteria for use with the api
    get historyContentQueryFields() {
        return Array.from(this.criteria)
            .map(([userField, val]) => {
                let serverField = this.getServerFieldName(userField);
                let serverVal = val;

                switch (serverField) {
                    // some client-side filters do not correspond to filters on the server
                    // they can be used to filter local results but will not affect the polling
                    // TODO: consider adding them as available filter options on the api?
                    case null:
                        return [];

                    // This is advertised to work, but is broken on the current api
                    case "annotation":
                    case "description":
                        return [];

                    // non-standard REST bools
                    // deleted serverField was reserved by pouchDB, needed to rename it to "isDeleted"
                    case "deleted":
                    case "visible":
                        serverVal = dumbBool(val);
                        break;

                    // no text searching in some fields
                    case "hid":
                    case "state":
                    case "history_content_type":
                    case "type":
                        break;

                    // assume text-contains search
                    default:
                        serverField = serverField + "-contains";
                        serverVal = encodeURIComponent(val);
                        break;
                }

                return [serverField, serverVal];
            })
            .filter((pair) => pair.length == 2)
            .reduce((fields, [k, v]) => {
                fields[k] = v;
                return fields;
            }, {});
    }

    // legacy q/qv syntax for content api
    // TODO: Delete when we no longer use q/qv
    get legacyContentQueryString() {
        return Object.entries(this.historyContentQueryFields)
            .map(([f, v]) => `q=${f}&qv=${v}`)
            .join("&");
    }

    // Standard query string (field=val&field=val...)
    get historyContentQueryString() {
        return Object.entries(this.historyContentQueryFields)
            .map(([f, v]) => `${f}=${v}`)
            .join("&");
    }

    // maps friendly user field name to internal data field if necessary
    getPouchFieldName(field) {
        const cleanName = field.replace(scrubFieldRE, "");
        return cleanName in pouchFieldAlias ? pouchFieldAlias[cleanName] : cleanName;
    }

    getServerFieldName(field) {
        const cleanName = field.replace(scrubFieldRE, "");
        return cleanName in serverFieldAlias ? serverFieldAlias[cleanName] : cleanName;
    }

    // output current state to log
    report(label = "params", collapsed = true) {
        const { showDeleted, showHidden, filterText } = this;
        const consoleOpen = collapsed ? console.groupCollapsed : console.group;
        consoleOpen.call(console, label);
        console.log("showDeleted", showDeleted);
        console.log("showHidden", showHidden);
        console.log("filterText", filterText);
        console.groupEnd();
    }
}

// Statics

SearchParams.pageSize = 30;

SearchParams.equals = function (a, b) {
    if (a !== undefined && b !== undefined) {
        return deepEqual(a.export(), b.export());
    }
    return false;
};
