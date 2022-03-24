/* Set of filter comparison operations. */
const filterOperation = {
    equal(attribute) {
        return {
            attribute,
            query: `${attribute}-eq`,
            handler: (v, q) => {
                return v == q;
            },
        };
    },
    includes(attribute) {
        return {
            attribute,
            query: `${attribute}-contains`,
            handler: (v, q) => {
                return v.includes(q);
            },
        };
    },
};

/* Valid filter fields and handlers which can be used for text searches. */
const validFilters = {
    extension: filterOperation.equal("extension"),
    format: filterOperation.equal("format"),
    hid: filterOperation.equal("hid"),
    history_content_type: filterOperation.equal("history_content_type"),
    name: filterOperation.includes("name"),
    state: filterOperation.equal("state"),
    tag: filterOperation.includes("tags"),
    type: filterOperation.equal("type"),
};

/* Parses single text input into a dict of field->value pairs. */
export function getFilters(filterText) {
    const validFields = new Set(Object.keys(validFilters));
    const pairSplitRE = /([A-Za-z0-9-]+=\w+)/g;
    const result = {};
    if (filterText.length == 0) {
        return [];
    }
    let matches = filterText.match(pairSplitRE);
    if (!matches && filterText.length > 0 && !filterText.includes("=")) {
        matches = [`name=${filterText}`];
    }
    if (matches) {
        matches.forEach((pair) => {
            const [field, value] = pair.split("=");
            if (validFields.has(field)) {
                result[field] = value;
            }
        });
    }
    return Object.entries(result);
}

/* Returns a dictionary with query key and values. */
export function getQueryDict(filterText) {
    const queryDict = {};
    const filters = getFilters(filterText);
    for (const [key, value] of filters) {
        const queryKey = validFilters[key].query;
        queryDict[queryKey] = value;
    }
    return queryDict;
}

/* Test if a value passes all filters. */
export function testFilter(filters, item) {
    for (const [key, value] of filters) {
        const filterValue = String(value).toLowerCase();
        const filterAttribute = validFilters[key].attribute;
        const filterHandler = validFilters[key].handler;
        const itemValue = String(item[filterAttribute]).toLowerCase();
        if (!filterHandler(itemValue, filterValue)) {
            return false;
        }
    }
    return true;
}
