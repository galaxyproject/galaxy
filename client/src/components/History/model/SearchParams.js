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

// Maps user-field -> server querystring field
// if maps to null, that filter not available on server
const serverFieldAlias = {
    tags: "tag",
    file_ext: null,
    genome_build: null,
};

// Convert boolean into python value as currently expected by the api
const pythonBool = (val) => (val ? "True" : "False");

export class SearchParams {
    constructor(props = {}) {
        this.filterText = "";
        this.showDeleted = false;
        this.showHidden = false;
        Object.assign(this, props);
    }

    // Filtering, parses single text input into a map of field->value
    // in the case of multiples, maps to field -> [value, value]
    get textCriteria() {
        const raw = this.filterText;

        const result = new Map();
        if (raw.length == 0) {
            return result;
        }

        let matches = raw.match(pairSplitRE);
        if (matches === null && raw.length > 0) {
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
                        serverVal = pythonBool(val);
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

    // Standard query string (field=val&field=val...)
    get historyContentQueryString() {
        return Object.entries(this.historyContentQueryFields)
            .map(([f, v]) => `${f}=${v}`)
            .join("&");
    }

    getServerFieldName(field) {
        const cleanName = field.replace(scrubFieldRE, "");
        return cleanName in serverFieldAlias ? serverFieldAlias[cleanName] : cleanName;
    }
}
