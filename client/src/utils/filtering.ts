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

import { omit } from "lodash";
import type { DefineComponent } from "vue";

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
export type Alias = keyof OperatorForAlias;
type Operator = OperatorForAlias[Alias];

interface RadioOption {
    text: string;
    value: string | number | boolean | Date | undefined;
}

/** A ValidFilter<T> for the Filtering<T> class, with its properties */
export type ValidFilter<T> = {
    /** The `FilterMenu` input field/tooltip/label placeholder */
    placeholder?: string;
    /** The data type of the `FilterMenu` input field */
    type?: typeof String | typeof Number | typeof Boolean | typeof Date;
    /** The handler function for this filter */
    handler: HandlerReturn<T>;
    /** Is this an filter to include as a field in `FilterMenu`? */
    menuItem?: boolean;
    /** Is there a datalist of values for this field */
    datalist?: string[];
    /** Is this a `FilterMenu` range filter?
     * (if yes, the `filter` key is taken and aliased into 2 input
     * fields: `filter-gt` & `filter-lt`)
     */
    isRangeInput?: boolean;
    /** The help info component to append to the `FilterMenu` input field */
    helpInfo?: DefineComponent | HTMLElement | string;
    /** The radio options if filter is a `FilterMenu` radio input */
    options?: RadioOption[];
};

/** Converts user input to backend compatible date
 * @param value
 * @returns seconds since epoch
 * */
export function toDate<T>(value: T): number {
    return Date.parse(String(value)) / 1000;
}

/** Converts user input for case-insensitive filtering
 * @param value
 * @returns Lowercase value
 * */
export function toLower<T>(value: T): string {
    return String(value).toLowerCase();
}

/** Converts user input to boolean (or undefined for null input)
 * @param value
 * @returns true/false if value is 'true/false', undefined if value is null
 * */
export function toBool<T>(value: T): boolean | undefined {
    return value !== null ? toLower(value) === "true" : undefined;
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
export function expandNameTag<T>(value: T): string {
    if (value && typeof value === "string") {
        value = value.replace(/^#/, "name:") as T;
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
    validFilters: Record<string, ValidFilter<T>>;
    validAliases: Array<[string, string]>;
    useDefaultFilters: boolean;
    defaultFilters: Record<string, T> = {
        deleted: false as T,
        visible: true as T,
    };

    constructor(
        validFilters: Record<string, ValidFilter<T>>,
        useDefaultFilters = true,
        validAliases?: Array<[string, string]>
    ) {
        this.validFilters = validFilters;
        this.useDefaultFilters = useDefaultFilters;
        this.validAliases = validAliases || defaultValidAliases;
    }

    /** Returns true if default filter values are not changed
     * @param filters Object containing filters
     * @returns true if default filter values are not changed
     * **/
    containsDefaults(filters: Record<string, T>): boolean {
        if (this.useDefaultFilters === false) {
            return false;
        }
        let hasDefaults = true;
        for (const key in this.defaultFilters) {
            const value = String(filters[key]).toLowerCase();
            const normalizedValue = String(this.defaultFilters[key]).toLowerCase();
            if (value !== normalizedValue) {
                hasDefaults = false;
                break;
            }
        }
        return hasDefaults;
    }

    /**
     * Returns true if filters Object contains all default keys
     * @param filters Object containing filter:value
     * @returns true if all default __keys__ are found in `filters`
     */
    hasAllDefaultKeys(filters: Record<string, T>): boolean {
        return (
            this.useDefaultFilters &&
            Object.keys(this.defaultFilters).every((def) => Object.keys(filters).includes(def))
        );
    }

    /** Build a text filter from filters {filter: "value", ...}
     * @param filters Object containing filters
     * @returns Parsed filter text string
     * */
    getFilterText(filters: Record<string, T>): string {
        filters = this.getValidFilters(filters);
        const hasDefaults = this.containsDefaults(filters);

        let newFilterText = "";
        Object.entries(filters).forEach(([key, value]) => {
            // this is a default filter, skip it if ALL default filters have default values
            const skipDefault = hasDefaults && this.defaultFilters[key] !== undefined;
            if (!skipDefault && value !== null && value !== undefined && value !== "") {
                if (newFilterText) {
                    newFilterText += " ";
                }
                if (String(value).includes(" ")) {
                    value = `'${value}'` as T;
                }
                newFilterText += `${this.toAliasKey(key)}${value}`;
            }
        });
        // enforce `filter:any` for any default *boolean* filters missing in filters object
        if (!hasDefaults && this.useDefaultFilters) {
            Object.entries(this.defaultFilters).forEach(([key, value]) => {
                if (filters[key] == undefined && typeof value === "boolean") {
                    if (newFilterText) {
                        newFilterText += " ";
                    }
                    newFilterText += `${this.toAliasKey(key)}any`;
                }
            });
        }
        return newFilterText;
    }

    /** Parses single text input into a dict of field->value pairs.
     * @param filterText Raw filter text string
     * @param removeAny default: `true` Whether to remove default filters if the are set to `any`
     * @returns Filters as 2D array of of [field, value] pairs
     * */
    getFiltersForText(filterText: string, removeAny = true): [string, T][] {
        const pairSplitRE = /[^\s'"]+(?:['"][^'"]*['"][^\s'"]*)*|(?:['"][^'"]*['"][^\s'"]*)+/g;
        const matches = filterText.match(pairSplitRE);
        let result: Record<string, T> = {};
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
                    const normalizedField = field?.split("-").join("_");
                    if (normalizedField && this.validFilters[normalizedField]) {
                        // removes quotation and applies lower-case to filter value
                        result[normalizedField] = toLowerNoQuotes(value) as T;
                        hasMatches = true;
                    }
                }
            });
        }
        // assume name matching if no filter key has been matched
        if (!hasMatches && filterText.length > 0) {
            result["name"] = filterText as T;
        }
        // check if any default filter keys have been used
        let hasDefaults = false;
        Object.keys(this.defaultFilters).forEach((defaultKey) => {
            const value = result[defaultKey];
            if (value !== undefined) {
                if (value == "any" && removeAny) {
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

    /**
     * Add (or remove) new filter(s) to existing filterText
     * @param filters New filter(s) to add
     * @param existingText Existing filterText to modify
     * @param remove default: `false` Whether to add or remove the new filter(s)
     * @returns Parsed `filterText` string with added/removed filter(s)
     */
    applyFiltersToText(filters: Record<string, T>, existingText: string, remove = false) {
        let validFilters = this.getValidFilters(filters);
        const existingFilters = Object.fromEntries(this.getFiltersForText(existingText, false));
        if (remove) {
            validFilters = omit(existingFilters, Object.keys(validFilters));
        } else {
            validFilters = Object.assign(existingFilters, validFilters);
        }
        return this.getFilterText(validFilters);
    }

    /** Takes a filters object and returns a new object with only valid filters
     *
     * @param filters A filters object (e.g.: {hid: "3", name: "test", invalid: "x"}})
     * @returns valid filters object (e.g.: {hid: "3", name: "test"}})
     */
    getValidFilters(filters: Record<string, T>) {
        const validFilters: Record<string, T> = {};
        Object.entries(filters).forEach(([key, value]) => {
            const validValue = this.getConvertedValue(key, value);
            if (validValue !== undefined) {
                validFilters[key] = validValue;
            }
        });
        return validFilters;
    }

    /** Convert a valid filter key (`filter`/`filter-gt`) to alias filter key (`filter:`/`filter>`)
     *  to use in creating `filterText` string.
     *
     * e.g.: filter = "hid-gt" becomes "hid>", filter = "hid" becomes "hid:"
     * @param filter Parsed filters object from getFiltersForText()
     * @returns filter key
     */
    toAliasKey(filter: string) {
        for (const [alias, substitute] of this.validAliases) {
            if (filter.endsWith(substitute)) {
                const keyPrefix = filter.slice(0, -substitute.length);
                return `${keyPrefix}${alias}`;
            }
        }
        return `${filter}:`;
    }

    /** Returns a dictionary with query key and values.
     * @param filterText Raw filter text string
     * @returns Dictionary with query key and values
     */
    getQueryDict(filterText: string) {
        const queryDict: Record<string, T> = {};
        const filters = this.getFiltersForText(filterText);
        for (const [key, value] of filters) {
            const query = this.validFilters[key]?.handler.query;
            const converter = this.validFilters[key]?.handler.converter;
            if (query) {
                queryDict[query] = converter ? converter(value) : value;
            }
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

    /**
     * Converts the `filterValue` to the correct type/format if there is a converter.
     * Note: Can use optional bool param to convert into backend format:
     * - `tag` filters for name tags (`#val` -> `name:val`)
     * - __time__ filters for `create_time` etc. (`dd-mm-yy` to `number`)
     * @param filterName The filter
     * @param filterValue The value being converted
     * @param backendFormatted default: `false` Whether to format values (tags or times) for backend
     * @returns converted value if there is a converter, else `filterValue`
     */
    getConvertedValue(filterName: string, filterValue: T, backendFormatted = false): T | undefined {
        if (this.validFilters[filterName]) {
            const { converter } = this.validFilters[filterName]?.handler as HandlerReturn<T>;
            if (converter) {
                if (converter == toBool && filterValue == "any") {
                    return filterValue;
                } else if (!backendFormatted && (converter == expandNameTag || converter == toDate)) {
                    return toLower(filterValue) as T;
                }
                return converter(filterValue);
            } else {
                return filterValue;
            }
        } else {
            return undefined;
        }
    }

    /** Check the value of a particular filter in given `filterText`.
     * @param filterText Raw filter text string
     * @param filterName Filter key to check
     * @param filterValue The filter value to check
     * @returns True if the filter is set to the given value
     * */
    checkFilter(filterText: string, filterName: string, filterValue: T): boolean {
        const testValue = this.getFilterValue(filterText, filterName);
        return toLowerNoQuotes(testValue) === toLowerNoQuotes(filterValue);
    }

    /** Get the value of a particular filter from filterText.
     * @param filterText Raw filter text string
     * @param filterName Filter key to check
     * @param backendFormatted default: `false` Whether to format values (tags or times) for backend
     * @returns The filterValue for the filter
     * */
    getFilterValue(filterText: string, filterName: string, backendFormatted = false): T | undefined {
        const filters = Object.fromEntries(this.getFiltersForText(filterText));
        let filterVal = filters[filterName];
        const defaultFilterValue = this.defaultFilters[filterName];
        if (filterVal !== undefined) {
            filterVal = this.getConvertedValue(filterName, filterVal, backendFormatted);
            return filterVal;
        } else if (defaultFilterValue !== undefined && typeof defaultFilterValue == "boolean") {
            filterVal = this.getConvertedValue(filterName, "any" as T, backendFormatted);
            return filterVal;
        }
        // if we don't have ALL defaultFilters in filters (a default filter is missing: val = "any")
        if (!this.hasAllDefaultKeys(filters)) {
            return filters[filterName];
        }

        return defaultFilterValue;
    }

    /**
     * Updates (inserts/removes) the filter:value in a filterText
     * @param filterText The filterText to update
     * @param newFilter The new filter key to update a value for
     * @param newVal The new value to update
     * @returns Parsed filterText string with added/removed filter
     */
    setFilterValue(filterText: string, newFilter: string, newVal: T) {
        let updatedText = "";
        const oldVal = this.getFilterValue(filterText, newFilter);
        const convVal = this.getConvertedValue(newFilter, newVal);
        if (convVal == undefined) {
            return filterText;
        }
        const settings = { [newFilter]: convVal };
        if (oldVal == convVal) {
            updatedText = this.applyFiltersToText(settings, filterText, true);
        } else {
            updatedText = this.applyFiltersToText(settings, filterText);
        }
        return updatedText;
    }

    /** Test if an item passes all filters.
     * @param filters Parsed in key-value pairs from getFiltersForText()
     * @param item Item to test against the filters
     * @returns True if the item passes all filters
     * */
    testFilters(filters: [string, T][], item: Record<string, T>): boolean {
        for (const [key, filterValue] of filters) {
            if (!(key in this.validFilters)) {
                console.error(`Invalid filter ${key}`);
            } else {
                const filterAttribute = this.validFilters[key]?.handler.attribute;
                const filterHandler = this.validFilters[key]?.handler.handler;
                const itemValue = filterAttribute && item[filterAttribute];
                if (itemValue === undefined || (filterHandler && itemValue && !filterHandler(itemValue, filterValue))) {
                    return false;
                }
            }
        }
        return true;
    }
}
