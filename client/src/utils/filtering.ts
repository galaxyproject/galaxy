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
const defaultValidAliases: Array<[string, string]> = [
    [">", "_gt"],
    ["<", "_lt"],
];

const operatorForAlias = {
    lt: "<",
    le: "<=",
    ge: ">=",
    gt: ">",
    eq: ":",
} as const satisfies Record<string, string>;

type OperatorForAlias = typeof operatorForAlias;
type Alias = keyof OperatorForAlias;
type Operator = OperatorForAlias[Alias];

/** Converts user input to backend compatible date
 * @param value
 * @returns seconds since epoch
 * */
export function toDate(value: string): number {
    return Date.parse(value) / 1000;
}

/** Converts user input for case-insensitive filtering
 * @param value
 * @returns Lowercase value
 * */
export function toLower<T>(value: T): string {
    return String(value).toLowerCase();
}

/** Converts user input to boolean
 * @param value
 * @returns true if value is 'true', false if value is 'false'
 * */
export function toBool<T>(value: T): boolean {
    return toLower(value) === "true";
}

/** Converts user input to lower case and strips quotation marks
 * @param value
 * @returns Lowercase value without quotation marks
 * */
export function toLowerNoQuotes<T>(value: T): string {
    return toLower(value).replace(/('|")/g, "");
}

/** Converts name tags starting with '#' to 'name:'
 * @param value
 * @returns Lowercase value with 'name:' replaced with '#'
 * */
export function expandNameTag(value: string | object): string {
    if (value && typeof value === "string") {
        value = value.replace(/^#/, "name:");
    }
    return toLower(value);
}

/** Converts string alias to string operator, e.g.: 'gt' to '>'
 * @param alias
 * @returns Arithmetic operator, e.g.: '>'
 * */
export function getOperatorForAlias(alias: Alias): Operator {
    return operatorForAlias[alias];
}

type HandlerReturn<T> = {
    attribute: string;
    converter?: Converter<T>;
    query: string;
    handler: Handler<T>;
};

/**
 * Checks if a query value is equal to the item value
 * @param attribute of the content item
 * @param query parameter if the attribute does not match the server query key
 * @param converter if item attribute value has to be transformed e.g. to a date.
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
 * @param attribute of the content item
 * @param query parameter if the attribute does not match the server query key
 * @param converter if item attribute value has to be transformed e.g. to a date.
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
 * @param attribute of the content item
 * @param variant specifying the comparison operation e.g. le(<=) and gt(>)
 * @param converter if item attribute value has to be transformed e.g. to a date.
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
    validAliases: Array<[string, string]>;
    useDefaultFilters: boolean;
    defaultFilters: Record<string, boolean> = {
        deleted: false,
        visible: true,
    };

    constructor(
        validFilters: Record<string, HandlerReturn<T>>,
        useDefaultFilters = true,
        validAliases?: Array<[string, string]>
    ) {
        this.validFilters = validFilters;
        this.useDefaultFilters = useDefaultFilters;
        this.validAliases = validAliases || defaultValidAliases;
    }

    /** Returns normalize defaults by adding the operator to the key identifier
     * @returns Dictionary with query key and values for default filters
     * */
    getDefaults(): Record<string, boolean> {
        const normalized: Record<string, boolean> = {};
        Object.entries(this.defaultFilters).forEach(([key, value]) => {
            normalized[`${key}:`] = value;
        });
        return normalized;
    }

    /** Returns true if default filter values are not changed
     * @param filterSettings Object containing filter settings
     * @returns true if default filter values are not changed
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
     * @param filterSettings Object containing filter settings
     * @returns Parsed filter text string
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
     * @param filterText Raw filter text string
     * @returns Filters as dict of field->value pairs
     * */
    getFilters(filterText: string): [string, T][] {
        const pairSplitRE = /[^\s'"]+(?:['"][^'"]*['"][^\s'"]*)*|(?:['"][^'"]*['"][^\s'"]*)+/g;
        const matches = filterText.match(pairSplitRE);
        let result: Record<string, any> = {};
        let hasMatches = false;
        if (matches) {
            matches.forEach((pair) => {
                const elgRE = /(\S+)([:><])(.+)/g;
                const elgMatch = elgRE.exec(pair);
                if (elgMatch) {
                    let field = elgMatch[1]!;
                    const elg = elgMatch[2]!;
                    const value = elgMatch[3]!;
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
        Object.keys(this.defaultFilters).forEach((defaultKey) => {
            const value = result[defaultKey];
            if (value !== undefined) {
                if (value == "any") {
                    delete result[defaultKey];
                }
                hasDefaults = true;
            }
        });
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
     * @param filters Parsed filterText from getFilters()
     * @returns filterSettings
     */
    toAlias(filters: [string, T][]) {
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
     * @param filterText Raw filter text string
     * @returns Dictionary with query key and values
     */
    getQueryDict(filterText: string) {
        const queryDict: Record<string, T> = {};
        const filters = this.getFilters(filterText);
        for (const [key, value] of filters) {
            const query = this.validFilters[key]!.query;
            const converter = this.validFilters[key]!.converter;
            queryDict[query] = converter ? converter(value) : value;
        }
        return queryDict;
    }

    /** Returns query string from filter text.
     * @param filterText Raw filter text string to be parsed
     * @returns Parsed query string
     * */
    getQueryString(filterText: string): string {
        const filterDict = this.getQueryDict(filterText);
        return Object.entries(filterDict)
            .map(([f, v]) => `q=${f}&qv=${v}`)
            .join("&");
    }

    /** Check the value of a particular filter.
     * @param filterText Raw filter text string
     * @param filterName Filter key to check
     * @param filterValue The filter value to check
     * @returns True if the filter is set to the given value
     * */
    checkFilter(filterText: string, filterName: string, filterValue: string | object | boolean): boolean {
        const testValue = this.getFilterValue(filterText, filterName);
        return toLowerNoQuotes(testValue) === toLowerNoQuotes(filterValue);
    }

    /** Get the value of a particular filter from filterText.
     * @param filterText Raw filter text string
     * @param filterName Filter key to check
     * @param alias default: `eq` String alias for filter operator, e.g.:"lt"
     * @returns The filterValue for the filter
     * */
    getFilterValue(filterText: string, filterName: string, alias: Alias = "eq"): string | boolean | undefined {
        const op = getOperatorForAlias(alias);
        const reString = `${filterName}(?:${op}|[-|_]${alias}:)(?:['"]([^'"]*[^\\s'"]*)['"]|(\\S+))`;
        const re = new RegExp(reString);
        const reMatch = re.exec(filterText);
        let filterVal = null;
        if (reMatch) {
            filterVal = reMatch[1] || reMatch[2];
        }
        return filterVal || this.defaultFilters[filterName];
    }

    /** Test if an item passes all filters.
     * @param filters Parsed in key-value pairs from getFilters()
     * @param item Item to test against the filters
     * @returns True if the item passes all filters
     * */
    testFilters(filters: [string, T][], item: Record<string, T>): boolean {
        for (const [key, filterValue] of filters) {
            if (!(key in this.validFilters)) {
                console.error(`Invalid filter ${key}`);
            } else {
                const filterAttribute = this.validFilters[key]!.attribute;
                const filterHandler = this.validFilters[key]!.handler;
                const itemValue = item[filterAttribute];
                if (itemValue === undefined || !filterHandler(itemValue, filterValue)) {
                    return false;
                }
            }
        }
        return true;
    }
}
