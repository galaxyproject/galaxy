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

import { isEqual, omit } from "lodash";
import type { DefineComponent } from "vue";

export type Converter<T> = (value: T) => T;
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

export type ErrorType = {
    filter: string;
    index?: string;
    value?: string;
    typeError?: string;
    msg: string;
};

type OperatorForAlias = typeof operatorForAlias;
export type Alias = keyof OperatorForAlias;
type Operator = OperatorForAlias[Alias];
export type FilterType =
    | typeof String
    | typeof Number
    | typeof Boolean
    | typeof Date
    | "MultiTags"
    | "ObjectStore"
    | "QuotaSource"
    | "Dropdown";

/** A ValidFilter<T> with a `handler` for the `Filtering<T>` class,
 * and remaining properties for the `FilterMenu` component
 * */
export type ValidFilter<T> = {
    /** The `FilterMenu` input field/tooltip/label placeholder */
    placeholder?: string;
    /** The data type of the `FilterMenu` input field */
    type?: FilterType;
    /** If type: Boolean:
     * - booleanType: 'default' creates: `filter:true|false|any`
     * - booleanType: 'is' creates: `is:filter`
     */
    boolType?: "default" | "is";
    /** The handler function for this filter */
    handler: HandlerReturn<T>;
    /** Is this a filter to include as a field in `FilterMenu`?
     * (if `false` the filter is still valid for the search bar `filterText`)
     */
    menuItem: boolean;
    /** The datalist of values for this field */
    datalist?:
        | string[]
        | {
              value: string;
              text: string;
          }[];
    /** Is this a `FilterMenu` range filter?
     * (if yes, the `filter` key is taken and aliased into 2 input
     * fields: `filter-gt` & `filter-lt`)
     */
    isRangeInput?: boolean;
    /** The help info component to append to the `FilterMenu` input field */
    helpInfo?: DefineComponent | string;
    /** A default value (will make this a default filter for an empty `filterText`) */
    default?: T;
    /** A dict of filters and corresponding values for this filter that disable them.
     * Note: if value is null, the filter is disabled for any value of this filter.
     */
    disablesFilters?: {
        [filter: string]: T[] | null;
    };
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

/** Whether a value is wrapped in a matching pair of surrounding quotes, e.g. `'foo'` or `"foo"`.
 * A quoted value signals an exact, case-sensitive backend match.
 * */
export function isQuoted<T>(value: T): boolean {
    return typeof value === "string" && /^(['"]).*\1$/.test(value);
}

/** Strips one layer of matching surrounding quotes, preserving case. Leaves unquoted values as is.
 * @param value
 * @returns The value without its surrounding quote pair
 * */
export function stripQuotes<T>(value: T): string {
    return isQuoted(value) ? String(value).slice(1, -1) : String(value);
}

/** Converts name tags starting with '#' to 'name:'
 * @param value
 * @returns String value with 'name:' replaced with '#'
 * */
export function expandNameTag<T>(value: T): string {
    if (value && typeof value === "string") {
        if ((value.startsWith("'#") || value.startsWith('"#')) && (value.endsWith('"') || value.endsWith("'"))) {
            value = value.replace(/^['"]#/g, "'name:") as T;
        } else {
            value = value.replace(/^#/, "name:") as T;
        }
    }
    return value as string;
}

/** Converts string alias to string operator, e.g.: 'gt' to '>'
 * @param alias
 * @returns Arithmetic operator, e.g.: '>'
 * */
export function getOperatorForAlias(alias: Alias): Operator {
    return operatorForAlias[alias];
}

export type HandlerReturn<T> = {
    attribute: string;
    converter?: Converter<T>;
    query: string;
    handler: Handler<T>;
};

/** One parsed unit of a `filterText` string, produced by `Filtering.tokenize`.
 * Everything the class needs downstream (quoted-ness, raw-text-ness, the typed operator) lives
 * here, so `filterText` is only ever tokenized once per operation.
 */
interface FilterToken {
    /** Normalized backend key (`create_time_gt`, not `create-time>`). `undefined` for raw text. */
    key?: string;
    /** The alias operator as typed (`:` / `>` / `<`), used to rebuild `filterText` exactly. */
    op?: ":" | ">" | "<";
    /** Value with surrounding quotes stripped (`quoteStrings`) or kept verbatim (`!quoteStrings`);
     * original case is always preserved at this layer. */
    value: string;
    /** The value was wrapped in a matching quote pair. The token's case should be preserved and
     * not lower cased. It does NOT by itself mean an exact match; see `exactMatch`. */
    quoted: boolean;
    /** An exact match request: the value was quoted AND has no whitespace (is single-word). */
    exactMatch: boolean;
    /** The token had no `key:value` shape -- unspecified text destined for `autoFilterKey`. */
    isRawText: boolean;
    /** The token used `is:key` syntax (means the boolean filter `key` is `true`). */
    isBool: boolean;
}

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

export function quotaSourceFilter<T>(attribute: string, converter: Converter<T>): HandlerReturn<T> {
    return {
        attribute: attribute,
        converter: converter,
        query: `${attribute}-eq`,
        handler: (v: T, q: T) => {
            if (converter) {
                v = converter(v);
                q = converter(q);
            }
            function handleNullConversion(v: T) {
                const lowerV = toLower(v);
                return lowerV == "__null__" ? "null" : lowerV;
            }
            return handleNullConversion(v) === handleNullConversion(q);
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
    /** Filter keys/values to apply when `filterText` is empty, built from `validFilters[key].default` */
    defaultFilters: Record<string, T>;

    /**
     * Class for filtering (menus). Handles user input as one string filterText
     * or multiple filters (e.g. 'name:foo type:bar'), with appropriate functions.
     * @param validFilters Record of valid filters with their handlers,
     *                      and FilterMenu properties (if menuItem = true)
     * @param validAliases Array of valid aliases for filters
     * @param quoteStrings Whether to auto quote filter strings in the query
     * @param autoFilterKey Filter key that unspecified text (e.g. 'foo' in 'foo type:bar') maps to,
     *                      e.g. 'name'. Must already be declared in `validFilters`. Omit to leave
     *                      unspecified text unmatched.
     */
    constructor(
        public validFilters: Record<string, ValidFilter<T>>,
        public validAliases: Array<[string, string]> = defaultValidAliases,
        public quoteStrings = true,
        public autoFilterKey?: string,
    ) {
        if (this.autoFilterKey !== undefined && this.validFilters[this.autoFilterKey] === undefined) {
            throw new Error(`Filtering: autoFilterKey "${this.autoFilterKey}" must be declared in validFilters`);
        }
        this.defaultFilters = this.createDefaultFiltersIfPresent();
        this.addRangedFiltersIfNotPresent();
    }

    /** For `FilterMenu` validFilters, if `isRangeInput`, then adds handlers
     * for the `lt` & `gt` filters if not included in `validFilters` already
     */
    addRangedFiltersIfNotPresent() {
        Object.entries(this.validFilters).forEach(([key, filter]) => {
            if (filter.isRangeInput) {
                const { converter } = filter.handler as HandlerReturn<T>;
                if (this.validFilters[`${key}_gt`] === undefined) {
                    this.validFilters[`${key}_gt`] = {
                        ...filter,
                        handler: compare(key, "gt", converter),
                        menuItem: false,
                    };
                }
                if (this.validFilters[`${key}_lt`] === undefined) {
                    this.validFilters[`${key}_lt`] = {
                        ...filter,
                        handler: compare(key, "lt", converter),
                        menuItem: false,
                    };
                }
            }
        });
    }

    /** If any `validFilters` are given the `default` key, a `defaultFilters`
     * object is created with provided values, that an empty `filterText`
     * corresponds to.
     * */
    createDefaultFiltersIfPresent(): Record<string, T> {
        const defaultFilters: Record<string, T> = {};
        Object.entries(this.validFilters).forEach(([key, filter]) => {
            if (filter.default !== undefined) {
                defaultFilters[key] = filter.default;
            }
        });
        return defaultFilters;
    }

    /** Returns true if default filter values are not changed
     * @param filters Object containing filters
     * @returns true if default filter values are not changed
     * **/
    containsDefaults(filters: Record<string, T>): boolean {
        if (this.defaultFilters === undefined) {
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
            this.defaultFilters !== undefined &&
            Object.keys(this.defaultFilters).every((def) => Object.keys(filters).includes(def))
        );
    }

    /** Splits a whitespace-trimmed `filterText` into its `key:value` (and raw-text) chunks.
     * The two `quoteStrings` modes tokenize incompatibly: `true` groups spaces with quotes and
     * allows bare raw text; `false` lets a value run unquoted up to the next `key:` token.
     */
    private splitPairs(filterText: string): { pairs: string[]; leadingText?: string } {
        filterText = filterText.trim();
        if (this.quoteStrings) {
            const re = /[^\s'"]+(?:['"][^'"]*['"][^\s'"]*)*|(?:['"][^'"]*['"][^\s'"]*)+/g;
            return { pairs: filterText.match(re) || [] };
        }
        const re = /(\S+):(.*?)(?=\s+\S+:|$)/g;
        const pairs = filterText.match(re) || [];
        // this regex only matches from the first `key:` onward, so any leading text is separate
        const firstMatchStart = pairs.length ? filterText.indexOf(pairs[0]!) : filterText.length;
        const leadingText = filterText.slice(0, firstMatchStart).trim();
        return { pairs, leadingText: leadingText || undefined };
    }

    /** Splits one `key:value` / `key>value` / `key<value` chunk into its parts, or `null` if it
     * has no such shape (i.e. it is raw text).
     */
    private splitKeyOpValue(pair: string): { field: string; op: ":" | ">" | "<"; value: string } | null {
        const match = /(\S+)([:><])(.+)/g.exec(pair);
        if (!match) {
            return null;
        }
        return { field: match[1]!, op: match[2] as ":" | ">" | "<", value: match[3]! };
    }

    /** Applies an alias substitution (`>` -> `_gt`) and normalizes dashes to underscores, turning a
     * typed field + operator into its normalized backend key (`create-time` + `>` -> `create_time_gt`).
     */
    private normalizeFieldKey(field: string, op: string): string {
        for (const [alias, substitute] of this.validAliases) {
            if (op === alias) {
                field = `${field}${substitute}`;
                break;
            }
        }
        return field.split("-").join("_");
    }

    /** Parses `filterText` into a flat token list, once. Preserves quoted-ness, raw-text-ness, and
     * the typed operator so no downstream method has to re-scan the source text.
     */
    private tokenize(filterText: string): FilterToken[] {
        const { pairs, leadingText } = this.splitPairs(filterText);
        const tokens: FilterToken[] = [];
        if (leadingText) {
            tokens.push({ value: leadingText, quoted: false, exactMatch: false, isRawText: true, isBool: false });
        }
        for (const pair of pairs) {
            const parts = this.splitKeyOpValue(pair);
            if (!parts) {
                tokens.push({ value: pair, quoted: false, exactMatch: false, isRawText: true, isBool: false });
                continue;
            }
            const { field, op, value } = parts;
            if (field === "is" && op === ":") {
                // `is:key` syntax -- the value names the boolean filter being set to true
                tokens.push({
                    key: value,
                    op,
                    value,
                    quoted: false,
                    exactMatch: false,
                    isRawText: false,
                    isBool: true,
                });
                continue;
            }
            const quoted = this.quoteStrings && isQuoted(value);
            tokens.push({
                key: this.normalizeFieldKey(field, op),
                op,
                value,
                quoted,
                // a quoted *multi-word* value is ambiguous -- see `FilterToken.exactMatch`
                exactMatch: quoted && !stripQuotes(value).includes(" "),
                isRawText: false,
                isBool: false,
            });
        }
        // A lone quoted bare token (e.g. `'Grep1'` typed on its own) is an exact-match request for
        // `autoFilterKey`: tag it with that key so it routes like a keyed quoted value.
        const rawTokens = tokens.filter((t) => t.isRawText);
        if (
            this.quoteStrings &&
            this.autoFilterKey !== undefined &&
            rawTokens.length === 1 &&
            isQuoted(rawTokens[0]!.value)
        ) {
            rawTokens[0]!.key = this.autoFilterKey;
            rawTokens[0]!.quoted = true;
            rawTokens[0]!.exactMatch = !stripQuotes(rawTokens[0]!.value).includes(" ");
        }
        return tokens;
    }

    /** Folds a token list into a `{key: value}` dict (the shape `getFiltersForText` returns before
     * default handling). Applies validity filtering, MultiTags array accumulation, the
     * `quoteStrings` quote-strip/lowercase rule, and `autoFilterKey` raw-text folding.
     */
    private parseTokensToDict(tokens: FilterToken[], validate: boolean): Record<string, T> {
        const result: Record<string, T> = {};
        const rawText: string[] = [];
        for (const token of tokens) {
            if (token.isRawText) {
                // a lone quoted bare token folds in with its quotes stripped (see `tokenize`)
                rawText.push(token.quoted ? stripQuotes(token.value) : token.value);
                continue;
            }
            if (token.isBool) {
                // `is:key` -- keep only if the named filter is really a `boolType: "is"` filter
                if (!validate || this.validFilters[token.value]?.boolType === "is") {
                    result[token.value] = true as T;
                }
                continue;
            }
            const key = token.key!;
            const isValid =
                this.validFilters[key]?.boolType !== "is" &&
                ((!validate && key !== "is") || this.validFilters[key] !== undefined);
            if (!isValid) {
                continue;
            }
            // A quoted value keeps its original case (exact, case-sensitive match); an unquoted
            // value is folded to lower case. Either way surrounding quotes are stripped here --
            // `getQueryDict`/`getFilterText` recover quoted-ness from the source text.
            const value = this.quoteStrings
                ? ((token.quoted ? stripQuotes(token.value) : toLowerNoQuotes(token.value)) as T)
                : (token.value as T);
            if (this.validFilters[key]?.type === "MultiTags") {
                if (result[key] === undefined) {
                    result[key] = [value] as T;
                } else {
                    (result[key] as T[]).push(value);
                }
            } else {
                result[key] = value;
            }
        }
        // fold unspecified text into the auto-filter key
        if (this.autoFilterKey !== undefined && rawText.length > 0) {
            const unmatchedText = rawText.join(" ");
            const existing = result[this.autoFilterKey];
            result[this.autoFilterKey] = (existing !== undefined ? `${existing} ${unmatchedText}` : unmatchedText) as T;
        }
        return result;
    }

    /**
     * The set of keys whose *surviving* value came from an `FilterToken.exactMatch`.
     * For a repeated key (`name:'Exact' name:partial`) only the last occurrence wins the value in
     * `parseTokensToDict`, so its exact-match status must win here too as an earlier quoted
     * occurrence must not leak exact-match routing onto a later, unquoted value for the same key.
     * MultiTags keys accumulate instead of overwriting, so every occurrence contributes
     * independently there, same as today.
     */
    private exactMatchByKey(tokens: FilterToken[]): Set<string> {
        const exactMatch = new Map<string, boolean>();
        for (const token of tokens) {
            // a raw-text token is only relevant here if `tokenize` tagged it with `autoFilterKey`
            // (a lone quoted bare token); an untagged raw-text token has no `key` and is skipped
            if (token.isBool || token.key === undefined) {
                continue;
            }
            const isMultiTags = this.validFilters[token.key]?.type === "MultiTags";
            if (isMultiTags) {
                exactMatch.set(token.key, (exactMatch.get(token.key) ?? false) || token.exactMatch);
            } else {
                // scalar key: the last token for this key determines both the value and its
                // exact-match status, matching `parseTokensToDict`'s last-one-wins overwrite
                exactMatch.set(token.key, token.exactMatch);
            }
        }
        return new Set([...exactMatch.entries()].filter(([, v]) => v).map(([k]) => k));
    }

    /**
     * The valid filter key whose backend query should be used for an exact, case-sensitive match
     * of `key` — a sibling `${key}_eq` filter if one is declared (e.g. `name` -> `name_eq`),
     * otherwise `key` itself.
     */
    private exactMatchKeyFor(key: string): string {
        return this.validFilters[`${key}_eq`] !== undefined ? `${key}_eq` : key;
    }

    /** Build a text filter from filters {filter: "value", ...} => "filter:value"
     * @param filters Object containing filters
     * @param backendFormatted If true, returns a string formatted for the backend
     * @param sourceFilterText The filterText `filters` came from, if any. Tokenized once to recover
     *                      intent `getFiltersForText` discards: whether `autoFilterKey`'s value was
     *                      unspecified text (write back as plain text) vs an explicit `key:value`
     *                      token, and which values the user quoted (re-emit quoted).
     * @returns Parsed filter text string
     * */
    getFilterText(filters: Record<string, T>, backendFormatted = false, sourceFilterText?: string): string {
        filters = this.getValidFilters(filters, backendFormatted).validFilters;
        const hasDefaults = this.containsDefaults(filters);
        // Tokenize the source text once to recover intent that `getFiltersForText` discards:
        // whether `autoFilterKey`'s value was unspecified text (write it back as plain text) and
        // which keys the user quoted for an exact match (re-emit them quoted so the intent survives).
        const sourceTokens = sourceFilterText !== undefined ? this.tokenize(sourceFilterText) : [];
        const unspecifiedTextKey =
            sourceFilterText !== undefined &&
            this.autoFilterKey !== undefined &&
            !sourceTokens.some((t) => !t.isRawText && !t.isBool && t.key === this.autoFilterKey)
                ? this.autoFilterKey
                : undefined;
        // Only an unambiguous exact-match quoting (single word, see `FilterToken.exactMatch`) is
        // re-emitted as quoted here -- a multi-word value gets re-quoted anyway below because it
        // has a space, but that quoting is purely syntactic and must not imply exact match.
        const exactMatchKeys = this.exactMatchByKey(sourceTokens);

        let newFilterText = "";
        Object.entries(filters).forEach(([key, value]) => {
            // this is a default filter, skip it if ALL default filters have default values
            const skipDefault = !backendFormatted && hasDefaults && this.defaultFilters[key] !== undefined;
            if (!skipDefault) {
                if (newFilterText) {
                    newFilterText += " ";
                }
                if (key === unspecifiedTextKey) {
                    // write unspecified text back as plain text, not `key:value` -- but keep it
                    // quoted if it was an unambiguous exact-match request (a lone quoted bare token)
                    newFilterText += exactMatchKeys.has(key) ? `'${stripQuotes(value)}'` : `${value}`;
                } else if (this.validFilters[key]?.type === Boolean && this.validFilters[key]?.boolType === "is") {
                    if (value === true) {
                        newFilterText += `is:${key}`;
                    }
                } else if (this.validFilters[key]?.type == "MultiTags" && Array.isArray(value) && value.length > 0) {
                    const convertedValues = value
                        .map((v) => this.getConvertedValue(key, v, backendFormatted))
                        .filter((v) => v !== undefined) as T[];
                    newFilterText += `${convertedValues.map((v) => `${this.toAliasKey(key)}${v}`).join(" ")}`;
                } else if (
                    this.quoteStrings &&
                    (exactMatchKeys.has(key) || isQuoted(value) || String(value).includes(" "))
                ) {
                    // re-emit quoted: the user quoted it in the source text for an exact match,
                    // it's already a quoted literal (e.g. from setFilterValue), or it contains a
                    // space and needs quoting to survive re-tokenizing (purely syntactic, no
                    // exact-match intent implied by this branch alone)
                    newFilterText += `${this.toAliasKey(key)}'${stripQuotes(value)}'`;
                } else {
                    newFilterText += `${this.toAliasKey(key)}${value}`;
                }
            }
        });
        // enforce `filter:any` for any default *boolean* filters missing in filters object
        if (!hasDefaults && this.defaultFilters !== undefined) {
            Object.entries(this.defaultFilters).forEach(([key, value]) => {
                if (
                    filters[key] == undefined &&
                    typeof value === "boolean" &&
                    this.validFilters[key]?.boolType !== "is"
                ) {
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
     * @param removeAny default: `true` Whether to remove default filters if they are set to `any`
     * @returns Filters as 2D array of of [field, value] pairs
     * */
    getFiltersForText(filterText: string, removeAny = true, validate = true): [string, T][] {
        return Object.entries(this.parseFilterText(this.tokenize(filterText), removeAny, validate));
    }

    /** Tokens -> `{key: value}` dict, applying validity, MultiTags, `autoFilterKey` folding, and
     * default-filter handling (`removeAny` and "inject defaults if none were specified"). This is
     * the single parse pass `getFiltersForText` and `getQueryDict` share.
     */
    private parseFilterText(tokens: FilterToken[], removeAny: boolean, validate: boolean): Record<string, T> {
        let result = this.parseTokensToDict(tokens, validate);
        if (this.defaultFilters !== undefined) {
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
            if (!hasDefaults) {
                result = { ...result, ...this.defaultFilters };
            }
        }
        return result;
    }

    /**
     * Add (or remove) new filter(s) to existing filterText
     * @param filters New filter(s) to add
     * @param existingText Existing filterText to modify
     * @param remove default: `false` Whether to add or remove the new filter(s)
     * @returns Parsed `filterText` string with added/removed filter(s)
     */
    applyFiltersToText(filters: Record<string, T>, existingText: string, remove = false) {
        let { validFilters } = this.getValidFilters(filters);
        const existingFilters = Object.fromEntries(this.getFiltersForText(existingText, false));
        if (remove) {
            validFilters = omit(existingFilters, Object.keys(validFilters));
        } else {
            validFilters = Object.assign(existingFilters, validFilters);
        }
        return this.getFilterText(validFilters, false, existingText);
    }

    /** Takes a filters object and returns a new object with only valid filters
     *
     * @param filters A filters object (e.g.: {hid: "3", name: "test", invalid: "x"}})
     * @param backendFormatted default: `false` Whether to convert the values to backend format
     * @returns a _valid_ filters object (e.g.: {hid: "3", name: "test"}}) and one with invalid filters
     */
    getValidFilters(filters: Record<string, T>, backendFormatted = false) {
        const validFilters: Record<string, T> = {};
        const invalidFilters: Record<string, T> = {};
        Object.entries(filters).forEach(([key, value]) => {
            if (this.validFilters[key]?.type === "MultiTags" && Array.isArray(value)) {
                const validValues = value
                    .map((v) => this.getConvertedValue(key, v, backendFormatted))
                    .filter((v) => v !== undefined) as T[];

                if (validValues.length > 0) {
                    validFilters[key] = validValues as T;
                }

                const invalidValues = value.filter(
                    (v) => !validValues.includes(this.getConvertedValue(key, v, backendFormatted) as T),
                );

                if (invalidValues.length > 0) {
                    invalidFilters[key] = invalidValues as T;
                }
            } else {
                const validValue = this.getConvertedValue(key, value, backendFormatted);
                if (validValue !== undefined) {
                    validFilters[key] = validValue;
                } else {
                    invalidFilters[key] = value;
                }
            }
        });
        return { validFilters, invalidFilters };
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
     *
     * An single-word, quoted filter value (`name:'GREP'`) is an exact, case-sensitive match: it
     * is routed through the filter's sibling `${key}_eq` handler if one exists (`name-eq`, which
     * the backend compares with `==`), rather than the default (`name-contains`, a case-insensitive
     * substring match). A *multi-word* quoted value (`name:'foo bar'`) is NOT treated as an
     * exact-match request, since quoting a value is also how `getFilterText` keeps a value with a
     * space as one token, so quoting alone is ambiguous once whitespace is involved.
     * The parsed value keeps its original case with the quotes stripped either way.
     *
     * @param filterText Raw filter text string
     * @returns Dictionary with query key and values
     */
    getQueryDict(filterText: string) {
        const queryDict: Record<string, T> = {};
        const tokens = this.tokenize(filterText);
        const exactMatchKeys = this.exactMatchByKey(tokens);
        const filters = Object.entries(this.parseFilterText(tokens, true, true));
        for (const [key, value] of filters) {
            const queryKey = exactMatchKeys.has(key) ? this.exactMatchKeyFor(key) : key;
            const handler = this.validFilters[queryKey]?.handler;
            const query = handler?.query;
            const converter = handler?.converter;
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
        if (
            this.validFilters[filterName] &&
            !Array.isArray(filterValue) &&
            filterValue !== null &&
            filterValue !== undefined &&
            filterValue !== ""
        ) {
            const { converter } = this.validFilters[filterName]?.handler as HandlerReturn<T>;
            if (converter) {
                if (
                    (converter == toBool && filterValue == "any") ||
                    (!backendFormatted && /^(['"]).*\1$/.test(filterValue as string)) ||
                    (!backendFormatted && ([expandNameTag, toDate] as Converter<T>[]).includes(converter))
                ) {
                    return filterValue;
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
        // if filterVal is an array, convert each value
        if (Array.isArray(filterVal)) {
            filterVal = filterVal
                .map((v) => this.getConvertedValue(filterName, v, backendFormatted))
                .filter((v) => v !== undefined) as T;
            return filterVal;
        } else if (filterVal !== undefined) {
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
        let convVal = this.getConvertedValue(newFilter, newVal) as T;
        if (convVal == undefined && !Array.isArray(newVal)) {
            return filterText;
        }
        // for MultiTags filter
        if (this.validFilters[newFilter]?.type === "MultiTags" || Array.isArray(oldVal)) {
            // if newVal is an array, convert each value, else put already converted val in array
            let valuesToAdd = Array.isArray(newVal)
                ? newVal.map((v) => this.getConvertedValue(newFilter, v)).filter((v) => v !== undefined)
                : [convVal];
            // if oldVal is an array, convert new value(s), and only add ones that aren't already in oldVal
            if (Array.isArray(oldVal)) {
                const updatedArr = [...oldVal] as T[];
                (valuesToAdd as T[]).forEach((value) => {
                    if (!oldVal.includes(value)) {
                        updatedArr.push(value);
                    } else {
                        updatedArr.splice(updatedArr.indexOf(value), 1);
                    }
                });
                valuesToAdd = updatedArr.length !== 0 ? updatedArr : oldVal;
            }
            convVal = valuesToAdd as T;
        }
        const settings = { [newFilter]: convVal };
        if (isEqual(oldVal, convVal) || oldVal == convVal) {
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
                const validFilter = this.validFilters[key];
                if (validFilter) {
                    const filterAttribute = validFilter.handler.attribute;
                    const filterHandler = validFilter.handler.handler;
                    const itemValue = item[filterAttribute];
                    if (itemValue === undefined || !filterHandler(itemValue, filterValue)) {
                        return false;
                    }
                }
            }
        }
        return true;
    }
}
