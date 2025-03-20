/**
 * Galaxy utilities comprises small functions, which at this point
 * do not require their own classes/files
 */

import axios, { type AxiosError, type AxiosResponse } from "axios";

import { getGalaxyInstance } from "@/app";
import { NON_TERMINAL_STATES } from "@/components/WorkflowInvocationState/util";
import { getAppRoot } from "@/onload/loadConfig";
import _l from "@/utils/localization";

export function stateIsTerminal(result: Record<string, any>) {
    return !NON_TERMINAL_STATES.includes(result.state);
}

/** Object with any internal structure. More specific key than built-in Object type */
export type AnyObject = Record<string | number | symbol, any>;

/**
 * Call callback on every object in an object recursively
 *
 * @param object object to traverse
 * @param callback ran on every nested child object
 */
export function deepEach<O extends AnyObject, V extends O[keyof O] extends AnyObject ? O[keyof O] : never>(
    object: Readonly<O>,
    callback: (object: V | AnyObject) => void
): void {
    Object.values(object).forEach((value) => {
        if (Boolean(value) && typeof value === "object") {
            callback(value);
            deepEach(value, callback);
        }
    });
}

/**
 * Identifies urls and replaces them with anchors
 *
 * @param inputText
 * @returns string with <a> anchor tags, wrapping found URLs and e-mail addresses
 */
export function linkify(inputText: string): string {
    let replacedText = inputText;

    // URLs starting with http://, https://, or ftp://
    const urlProtocolPattern = /(\b(https?|ftp):\/\/[-A-Z0-9+&@#/%?=~_|!:,.;]*[-A-Z0-9+&@#/%=~_|])/gim;
    replacedText = replacedText.replace(urlProtocolPattern, '<a href="$1" target="_blank">$1</a>');

    // URLs starting with "www." (without // before it, or it'd re-link the ones done above).
    const urlPattern = /(^|[^/])(www\.[\S]+(\b|$))/gim;
    replacedText = replacedText.replace(urlPattern, '$1<a href="http://$2" target="_blank">$2</a>');

    // Change email addresses to mailto:: links.
    const emailPattern = /(([a-zA-Z0-9\-_.])+@[a-zA-Z_]+?(\.[a-zA-Z]{2,6})+)/gim;
    replacedText = replacedText.replace(emailPattern, '<a href="mailto:$1">$1</a>');

    return replacedText;
}

/**
 * @deprecated in favor of built in `structuredClone` method
 *
 * This is a deep copy of the object input
 */
export function clone<T>(obj: Readonly<T>): T {
    return JSON.parse(JSON.stringify(obj));
}

/**
 * Check if a string is a json string
 *
 * @param text Content to be validated
 */
export function isJSON(text: string): boolean {
    return /^[\],:{}\s]*$/.test(
        text
            .replace(/\\["\\/bfnrtu]/g, "@")
            .replace(/"[^"\\\n\r]*"|true|false|null|-?\d+(?:\.\d*)?(?:[eE][+-]?\d+)?/g, "]")
            .replace(/(?:^|:|,)(?:\s*\[)+/g, "")
    );
}

const emptyValues = ["__null__", "__undefined__", null, undefined] as const;

/**
 * Checks if a value or list of values is "empty".
 * Usually used for selectable options
 *
 * Considers `null`, `undefined` and the string literals `__null__`, `__undefined__` as "empty"
 *
 * @param value Value or list of values to be validated
 */
export function isEmpty(value: any | Readonly<any[]>) {
    if (!Array.isArray(value)) {
        return emptyValues.includes(value);
    } else {
        if (value.length === 0) {
            return true;
        }

        for (let index = 0; index < value.length; index++) {
            if (emptyValues.includes(value[index])) {
                return true;
            }
        }

        return false;
    }
}

/**
 * Convert list to pretty string.
 *
 * @example ```
 * const list = [1, 2, 3];
 * const pretty = textify(list);
 * console.log(pretty);
 * // outputs => 1, 2 or 3
 * ```
 *
 * @param list List of strings to be converted in human readable list sentence
 */
export function textify(list: Readonly<string[]>): string {
    let string = list.toString().replace(/,/g, ", ");
    const pos = string.lastIndexOf(", ");

    if (pos !== -1) {
        string = `${string.substring(0, pos)} or ${string.substring(pos + 2)}`;
    }

    return string;
}

/**
 * Request handler for GET.
 *
 * @property url     Url request is made to
 * @property success Callback on success
 * @property error   Callback on error
 * @property data    parameters to be sent with the request
 */
interface getOptions {
    url: string;
    data?: any;
    success?: (data: AxiosResponse) => void;
    error?: (error: AxiosError) => void;
}

/**
 * @deprecated legacy layer for old $.ajax interface
 * @param options
 */
export function get(options: getOptions): void {
    axios
        .get(options.url, { params: options.data })
        .then((response) => {
            if (options.success) {
                options.success(response.data);
            }
        })
        .catch((error) => {
            // I don't believe any consumers actually use this, just drop it as
            // we remove this interface
            if (options.error) {
                options.error(error);
            }
        });
}

/**
 * Safely merge two dictionaries
 *
 * @param options        Target dictionary
 * @param optionsDefault Source dictionary
 *
 * @returns modified options dictionary or new object
 */
export function merge(options: AnyObject | null | undefined, optionsDefault: Readonly<AnyObject>) {
    const object = options ?? {};

    Object.entries(optionsDefault).forEach(([key, value]) => {
        if (!object[key]) {
            object[key] = value;
        }
    });

    return object;
}

/**
 * Round floating point `number` to `numPlaces` number of decimal places.
 *
 * @param number    a floating point number
 * @param numPlaces number of decimal places
 */
export function roundToDecimalPlaces(number: number, numPlaces: number) {
    return parseFloat(number.toFixed(numPlaces));
}

const kb = 1024;
const mb = kb * kb;
const gb = mb * kb;
const tb = gb * kb;

/**
 * Format byte size to string with units
 *
 * @param size       Size in bytes
 * @param normalFont Switches font between normal and bold
 * @param numPlaces  decimalPlaces to round to
 *
 * @returns string representation of bytes,
 * or `strong` tag with size in bytes and unit (as string),
 * or `strong` tag with "-" (as string)
 */
export function bytesToString(size: number, normalFont = true, numPlaces = 1) {
    let unit = "";

    if (size >= tb) {
        size = size / tb;
        unit = "TB";
    } else if (size >= gb) {
        size = size / gb;
        unit = "GB";
    } else if (size >= mb) {
        size = size / mb;
        unit = "MB";
    } else if (size >= kb) {
        size = size / kb;
        unit = "KB";
    } else if (size > 0) {
        unit = "b";
    } else {
        return normalFont ? "0 b" : "<strong>-</strong>";
    }

    const rounded = unit == "b" ? size : roundToDecimalPlaces(size, numPlaces);

    if (normalFont) {
        return `${rounded} ${unit}`;
    } else {
        return `<strong>${rounded}</strong> ${unit}`;
    }
}

let idCounter = 0;

/**
 * @deprecated in favor of useUid composable
 *
 * Create a unique id
 */
export function uid(): string {
    idCounter += 1;
    return `uid-${idCounter}`;
}

/** Create a time stamp */
export function time(): string {
    const d = new Date();
    const hours = (d.getHours() < 10 ? "0" : "") + d.getHours();
    const minutes = (d.getMinutes() < 10 ? "0" : "") + d.getMinutes();
    return `${d.getDate()}/${d.getMonth() + 1}/${d.getFullYear()}, ${hours}:${minutes}`;
}

/**
 * Append script and style tags to Galaxy main application
 *
 * @param data object containing script and style strings
 */
export function appendScriptStyle(data: Readonly<{ script?: string; styles?: string }>) {
    // create a script tag inside head tag
    if (data.script && data.script !== "") {
        const tag = document.createElement("script");
        tag.type = "text/javascript";
        tag.textContent = data.script;
        document.head.appendChild(tag);
    }
    // create a style tag inside head tag
    if (data.styles && data.styles !== "") {
        const tag = document.createElement("style");
        tag.textContent = data.styles;
        document.head.appendChild(tag);
    }
}

export function setWindowTitle(title: string): void {
    const Galaxy = getGalaxyInstance();
    if (title) {
        window.document.title = `Galaxy ${Galaxy.config.brand ? ` | ${Galaxy.config.brand}` : ""} | ${_l(title)}`;
    } else {
        window.document.title = `Galaxy ${Galaxy.config.brand ? ` | ${Galaxy.config.brand}` : ""}`;
    }
}

/**
 * Calculate a 32 bit FNV-1a hash
 * Found here: https://gist.github.com/vaiorabbit/5657561
 * Ref.: http://isthe.com/chongo/tech/comp/fnv/
 *
 * @param str the input value
 * @returns integer number
 */
export function hashFnv32a(str: string): number {
    let hval = 0x811c9dc5;

    for (let i = 0, l = str.length; i < l; i++) {
        hval ^= str.charCodeAt(i);
        hval += (hval << 1) + (hval << 4) + (hval << 7) + (hval << 8) + (hval << 24);
    }
    return hval >>> 0;
}

/**
 * Return a promise, resolve it when element appears
 *
 * @param selector css selector
 *
 * @returns Element
 */
export async function waitForElementToBePresent(selector: string) {
    while (document.querySelector(selector) === null) {
        await new Promise((resolve) => requestAnimationFrame(resolve));
    }

    return document.querySelector(selector) as Element;
}

/**
 * Async `setTimeout` utility.
 * Resolves promise after set time
 *
 * @param milliseconds amount of time to wait in milliseconds
 */
export function wait(milliseconds: number) {
    return new Promise<void>((resolve) => {
        setTimeout(() => resolve(), milliseconds);
    });
}

/**
 * Merges two arrays of objects with unique id values into a single array.
 * If an object with the same id exists in both arrays, the object from the
 * newList will overwrite the object from the oldList. The merged array will
 * be sorted by the sortKey in the sortDirection.
 * @param oldList The original array of objects.
 * @param newList The array of objects to merge into the original array.
 * @param sortKey If provided, the merged array will be sorted by this key.
 * @param sortDirection If sortKey is provided, the merged array will be sorted in this direction.
 * @returns An array of merged objects.
 */
export function mergeObjectListsById<T extends { id: string; [key: string]: any }>(
    oldList: T[],
    newList: T[],
    sortKey: string | null = null,
    sortDirection: "asc" | "desc" = "desc"
): T[] {
    const idToObjMap: { [key: string]: T } = oldList.reduce((acc, obj) => ({ ...acc, [obj.id]: obj }), {});

    newList.forEach((obj) => {
        idToObjMap[obj.id] = obj;
    });

    const mergedList = Object.values(idToObjMap);

    if (sortKey) {
        mergedList.sort((a, b) => (a[sortKey] < b[sortKey] ? -1 : 1) * (sortDirection === "asc" ? 1 : -1));
    }

    return mergedList;
}

export function parseBool(value: string): boolean {
    return value.toLowerCase() === "true";
}

type MatchObject<T extends string | number | symbol, R> = {
    [_Case in T]: () => R;
};

/**
 * Alternative to `switch` statement.
 * Unlike `switch` it is exhaustive and allows for returning a value.
 *
 * @param key A key with the type of a Union of possible keys
 * @param matcher An object with a key for every possible match and a function as value, which will be ran if a match occurs
 * @returns The ran functions return value
 *
 * @example
 * ```ts
 * type literal = "a" | "b";
 * const thing = "a" as literal;
 *
 * const result = match(thing, {
 *   a: () => 1,
 *   b: () => 2,
 * });
 *
 * result === 1;
 * ```
 */
export function match<T extends string | number | symbol, R>(key: T, matcher: MatchObject<T, R>): R {
    return matcher[key]();
}

/**
 * Checks whether or not an object contains all supplied keys.
 *
 * @param object Object to check
 * @param keys Array of all keys to check for
 * @returns if all keys were found
 */
export function hasKeys(object: unknown, keys: string[]) {
    if (typeof object === "object" && object !== null) {
        let valid = true;
        keys.forEach((key) => (valid = valid && key in object));
        return valid;
    } else {
        return false;
    }
}

/**
 * Get the full URL path of the app
 *
 * @param path Path to append to the URL path
 * @returns Full URL path of the app
 */
export function getFullAppUrl(path: string = ""): string {
    const protocol = window.location.protocol;
    const hostname = window.location.hostname;
    const port = window.location.port ? `:${window.location.port}` : "";
    const appRoot = getAppRoot();

    return `${protocol}//${hostname}${port}${appRoot}${path}`;
}

export default {
    get,
    merge,
    bytesToString,
    uid,
    time,
    textify,
    isEmpty,
    deepEach,
    isJSON,
    clone,
    linkify,
    appendScriptStyle,
    setWindowTitle,
    waitForElementToBePresent,
    wait,
    mergeObjectListsById,
    getFullAppUrl,
};
