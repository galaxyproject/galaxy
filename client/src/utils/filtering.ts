/**
 * This utility function is used to parse and convert the user inputted filter text in `QUERY:VALUE` format to a query
 * object that can be sent to the server.
 * User input text is split by space and each filter can be in the following format:
 * `QUERY[:, < or >]VALUE`
 * QUERY may only contain alphanumeric characters, underscores, and dashes. Quotation marks are only allowed in `VALUE`
 * for values that contain spaces.
 * Each query key has a default suffix defined e.g. name:foo will be converted to name-eq:foo.
 * Comparison aliases are allowed converting e.g. '>' to '-gt' and '<' to '-lt'.
 */

type Converter<T> = (value: T) => T;
type Handler<T> = (v: T, q: T) => boolean;

/** Add comparison aliases i.e. '*>value' is converted to '*_gt=value' */
const defaultValidAliases = [
    [">", "_gt"],
    ["<", "_lt"],
];

/** Converts user input to backend compatible date
 * @param {string} value
 * @returns {Number} seconds since epoch
 * */
export function toDate(value: string): number {
    return Date.parse(value) / 1000;
}

/** Converts user input for case-insensitive filtering
 * @param {string} value
 * @returns {string} Lowercase value
 * */
export function toLower<T>(value: T): string {
    return String(value).toLowerCase();
}

/** Converts user input to boolean
 * @param {string} value
 * @returns {boolean} true if value is 'true', false if value is 'false'
 * */
export function toBool<T>(value: T): boolean {
    return toLower(value) === "true";
}

/** Converts user input to lower case and strips quotation marks
 * @param {string} value
 * @returns {string} Lowercase value without quotation marks
 * */
export function toLowerNoQuotes<T>(value: T): string {
    return toLower(value).split("'").join("");
}

/** Converts name tags starting with '#' to 'name:'
 * @param {string} value
 * @returns {string} Lowercase value with 'name:' replaced with '#'
 * */
export function expandNameTag(value: string | object): string {
    if (value && typeof value === "string" && value.startsWith("#")) {
        value = value.replace("#", "name:");
    }
    return toLower(value);
}

type HandlerReturn<T> = {
    attribute: string;
    converter?: Converter<T>;
    query: string;
    handler: Handler<T>;
};

/**
 * Checks if a query value is equal to the item value
 * @param {string} attribute of the content item
 * @param {string} [query] parameter if the attribute does not match the server query key
 * @param {function} [converter] if item attribute value has to be transformed e.g. to a date.
 */
export function equals<T>(attribute: string, query?: string, converter?: Converter<T>): HandlerReturn<T> {
    return {
        attribute,
        converter,
        query: query || `${attribute}-eq`,
        handler: (v: T, q: T) => {
            if (converter) {
                v = converter(v);
                q = converter(q);
            }
            return toLower(v) === toLower(q);
        },
    };
}

/**
 * Checks if a query value is part of the item value
 * @param {string} attribute of the content item
 * @param {string} [query] parameter if the attribute does not match the server query key
 * @param {function} [converter] if item attribute value has to be transformed e.g. to a date.
 */
export function contains<T>(attribute: string, query?: string, converter?: Converter<T>): HandlerReturn<T> {
    return {
        attribute,
        converter,
        query: query || `${attribute}-contains`,
        handler: (v: T, q: T) => {
            if (converter) {
                v = converter(v);
                q = converter(q);
            }
            return toLower(v).includes(toLower(q));
        },
    };
}

/**
 * Checks if a value is greater or smaller than the item value
 * @param {string} attribute of the content item
 * @param {string} variant specifying the comparison operation e.g. le(<=) and gt(>)
 * @param {function} [converter] if item attribute value has to be transformed e.g. to a date.
 */
export function compare<T>(attribute: string, variant: string, converter?: Converter<T>): HandlerReturn<T> {
    return {
        attribute,
        converter,
        query: `${attribute}-${variant}`,
        handler: (v: T, q: T) => {
            if (converter) {
                v = converter(v);
                q = converter(q);
            }
            switch (variant) {
                case "lt":
                    return v < q;
                case "le":
                    return v <= q;
                case "ge":
                    return v >= q;
                case "gt":
                    return v > q;
                default:
                    return false;
            }
        },
    };
}

export default class Filtering<T> {
    validFilters: Record<string, HandlerReturn<T>>;
    validAliases: string[][];
    useDefaultFilters: boolean;
    defaultFilters: Record<string, boolean> = {
        deleted: false,
        visible: true,
    };

    constructor(validFilters: Record<string, HandlerReturn<T>>, useDefaultFilters = true, validAliases?: string[][]) {
        this.validFilters = validFilters;
        this.useDefaultFilters = useDefaultFilters;
        this.validAliases = validAliases || defaultValidAliases;
    }

    /** Returns normalize defaults by adding the operator to the key identifier
     * @returns {Object} Dictionary with query key and values for default filters
     * */
    getDefaults(): Record<string, boolean> {
        const normalized: Record<string, boolean> = {};
        Object.entries(this.defaultFilters).forEach(([key, value]) => {
            normalized[`${key}:`] = value;
        });
        return normalized;
    }

    /** Returns true if default filter values are not changed
     * @param {Object} filterSettings Object containing filter settings
     * @returns {Boolean} True if default filter values are not changed
     * **/
    containsDefaults(filterSettings: Record<string, string | boolean>): boolean {
        const normalized = this.getDefaults();
        let hasDefaults = true;
        for (const key in normalized) {
            const value = String(filterSettings[key]).toLowerCase();
            const normalizedValue = String(normalized[key]).toLowerCase();
            if (value !== normalizedValue) {
                hasDefaults = false;
                break;
            }
        }
        return hasDefaults;
    }

    /** Build a text filter from filter settings
     * @param {Object} filterSettings Object containing filter settings
     * @returns {String} Parsed filter text string
     * */
    getFilterText(filterSettings: Record<string, string | boolean>): string {
        const normalized = this.getDefaults();
        const hasDefaults = this.containsDefaults(filterSettings);

        let newFilterText = "";
        Object.entries(filterSettings).forEach(([key, value]) => {
            const skipDefault = hasDefaults && normalized[key] !== undefined;
            if (!skipDefault && value !== undefined && value !== "") {
                if (newFilterText) {
                    newFilterText += " ";
                }
                if (String(value).includes(" ")) {
                    value = `'${value}'`;
                }
                newFilterText += `${key}${value}`;
            }
        });
        return newFilterText;
    }

    /** Parses single text input into a dict of field->value pairs.
     * @param {string} filterText Raw filter text string
     * @returns {object} Filters as dict of field->value pairs
     * */
    getFilters(filterText: string): [string, T][] {
        const pairSplitRE = /[^\s']+(?:'[^']*'[^\s']*)*|(?:'[^']*'[^\s']*)+/g;
        const matches = filterText.match(pairSplitRE);
        let result: Record<string, any> = {};
        let hasMatches = false;
        if (matches) {
            matches.forEach((pair) => {
                const elgRE = /(\S+)([:><])(.+)/g;
                const elgMatch = elgRE.exec(pair);
                if (elgMatch) {
                    let field = elgMatch[1];
                    const elg = elgMatch[2];
                    const value = elgMatch[3];
                    // replace alias for less and greater symbol
                    for (const [alias, substitute] of this.validAliases) {
                        if (elg === alias) {
                            field = `${field}${substitute}`;
                            break;
                        }
                    }
                    // replaces dashes with underscores in query field names
                    const normalizedField = field.split("-").join("_");
                    if (this.validFilters[normalizedField]) {
                        // removes quotation and applies lower-case to filter value
                        result[normalizedField] = toLowerNoQuotes(value);
                        hasMatches = true;
                    }
                }
            });
        }
        // assume name matching if no filter key has been matched
        if (!hasMatches && filterText.length > 0) {
            result["name"] = filterText;
        }
        // check if any default filter keys have been used
        let hasDefaults = false;
        for (const defaultKey in this.defaultFilters) {
            if (result[defaultKey]) {
                hasDefaults = true;
                break;
            }
        }
        // use default filters if none of the default filters has been explicitly specified
        if (!hasDefaults && this.useDefaultFilters) {
            result = { ...result, ...this.defaultFilters };
        }

        return Object.entries(result);
    }

    /** Returns a dictionary resembling filterSettings (for HistoryFilters):
     * e.g.: Unlike getFilters or getQueryDict, this maintains "hid>":"3" instead
     *       of changing it to "hid-gt":"3"
     * Only used to sync filterSettings (in HistoryFilters)
     * @param {Object} filters Parsed filterText from getFilters()
     * @returns {Object} filterSettings
     */
    toAlias(filters: [string, T][]): object {
        const result: Record<string, T> = {};
        for (const [key, value] of filters) {
            let hasAlias = false;
            for (const [alias, substitute] of this.validAliases) {
                if (key.endsWith(substitute)) {
                    const keyPrefix = key.slice(0, -substitute.length);
                    result[`${keyPrefix}${alias}`] = value;
                    hasAlias = true;
                    break;
                }
            }
            if (!hasAlias) {
                result[`${key}:`] = value;
            }
        }
        return result;
    }

    /** Returns a dictionary with query key and values.
     * @param {String} filterText Raw filter text string
     * @returns {Object} Dictionary with query key and values
     */
    getQueryDict(filterText: string): object {
        const queryDict: Record<string, T> = {};
        const filters = this.getFilters(filterText);
        for (const [key, value] of filters) {
            const query = this.validFilters[key].query;
            const converter = this.validFilters[key].converter;
            queryDict[query] = converter ? converter(value) : value;
        }
        return queryDict;
    }

    /** Returns query string from filter text.
     * @param {String} filterText Raw filter text string to be parsed
     * @returns {String} Parsed query string
     * */
    getQueryString(filterText: string): string {
        const filterDict = this.getQueryDict(filterText);
        return Object.entries(filterDict)
            .map(([f, v]) => `q=${f}&qv=${v}`)
            .join("&");
    }

    /** Check the value of a particular filter.
     * @param {String} filterText Raw filter text string
     * @param {String} filterName Filter key to check
     * @param {String | Object | Boolean} filterValue The filter value to check
     * @returns {Boolean} True if the filter is set to the given value
     * */
    checkFilter<T>(filterText: string, filterName: string, filterValue: T): boolean {
        const re = new RegExp(`${filterName}:(\\S+)`);
        const reMatch = re.exec(filterText);
        const testValue = reMatch ? reMatch[1] : this.defaultFilters[filterName];
        return toLowerNoQuotes(testValue) === toLowerNoQuotes(filterValue);
    }

    /** Test if an item passes all filters.
     * @param {Object} filters Parsed in key-value pairs from getFilters()
     * @param {Object} item Item to test against the filters
     * @returns {Boolean} True if the item passes all filters
     * */
    testFilters(filters: [string, T][], item: Record<string, T>): boolean {
        for (const [key, filterValue] of filters) {
            const filterAttribute = this.validFilters[key].attribute;
            const filterHandler = this.validFilters[key].handler;
            const itemValue = item[filterAttribute];
            if (!filterHandler(itemValue, filterValue)) {
                return false;
            }
        }
        return true;
    }
}
