/**
 * Galaxy utilities comprises small functions, which at this point
 * do not require their own classes/files
 */

import _ from "underscore";
import $ from "jquery";
import axios, { type AxiosError, type AxiosResponse } from "axios";

import { getAppRoot } from "@/onload/loadConfig";
import { getGalaxyInstance } from "@/app";
import _l from "@/utils/localization";

/** Object with any internal structure. More specific key than built-in Object type */
export type AnyObject = Record<string | number | symbol, any>;

/**
 * Call callback on every object in an object recursively
 *
 * @param object object to traverse
 * @param callback ran on every nested child object
 */
export function deepEach<O extends AnyObject, V extends O[keyof O] extends AnyObject ? O[keyof O] : never>(
    object: O,
    callback: (object: V | AnyObject) => void
): void {
    Object.values(object).forEach((value) => {
        if (typeof value === "object") {
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
export function clone<T>(obj: T): T {
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
export function isEmpty(value: any | any[]) {
    if (!Array.isArray(value)) {
        if (emptyValues.includes(value)) {
            return true;
        } else {
            return false;
        }
    } else {
        for (let index = 0; index < value.length; index++) {
            if (emptyValues.includes(value[index])) {
                return true;
            }
        }

        return false;
    }
}

/**
 * Convert list to pretty string
 * @param{String}   lst - List of strings to be converted in human readable list sentence
 */
export function textify(lst: string[] | string): string {
    if (Array.isArray(lst)) {
        lst = lst.toString().replace(/,/g, ", ");
        const pos = lst.lastIndexOf(", ");
        if (pos != -1) {
            lst = `${lst.substr(0, pos)} or ${lst.substr(pos + 2)}`;
        }
        return lst;
    }
    return "";
}

/**
 * Request handler for GET
 * legacy layer from old $.ajax interface
 * @param{String}   url     - Url request is made to
 * @param{Function} success - Callback on success
 * @param{Function} error   - Callback on error
 * @param{Object}   data    - parameters to be sent with the request
 */
interface getOptions {
    url: string;
    data?: any;
    success?: (data: AxiosResponse) => void;
    error?: (error: AxiosError) => void;
}

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
 * Read a property value from CSS
 * @param{String}   classname   - CSS class
 * @param{String}   name        - CSS property
 */
export function cssGetAttribute(classname: string, name: string): string {
    const el = $(`<div class="${classname}"></div>`);
    el.appendTo(":eq(0)");
    const value = el.css(name);
    el.remove();
    return value;
}

/**
 * Load a CSS file
 * @param{String}   url - Url of CSS file
 */
export function cssLoadFile(url: string): void {
    if (!$(`link[href^="${url}"]`).length) {
        $(`<link href="${getAppRoot()}${url}" rel="stylesheet">`).appendTo("head");
    }
}

/**
 * Safely merge to dictionaries
 * @param{Object}   options         - Target dictionary
 * @param{Object}   optionsDefault  - Source dictionary
 */
export function merge(options: any, optionsDefault: any) {
    if (options) {
        return _.defaults(options, optionsDefault);
    } else {
        return optionsDefault;
    }
}

/**
 * Round floating point 'number' to 'numPlaces' number of decimal places.
 * @param{number}   number      a floaing point number
 * @param{number}   numPlaces   number of decimal places
 */
export function roundToDecimalPlaces(number: number, numPlaces: number) {
    let placesMultiplier = 1;
    for (let i = 0; i < numPlaces; i++) {
        placesMultiplier *= 10;
    }
    return Math.round(number * placesMultiplier) / placesMultiplier;
}

// calculate on import
const kb = 1024;
const mb = kb * kb;
const gb = mb * kb;
const tb = gb * kb;

/**
 * Format byte size to string with units
 * @param{Integer}   size           - Size in bytes
 * @param{Boolean}   normal_font    - Switches font between normal and bold
 */
export function bytesToString(size: number, normal_font: boolean, numPlaces = 1) {
    // identify unit
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
        return normal_font ? "0 b" : "<strong>-</strong>";
    }
    // return formatted string
    const rounded = unit == "b" ? size : roundToDecimalPlaces(size, numPlaces);
    if (normal_font) {
        return `${rounded} ${unit}`;
    } else {
        return `<strong>${rounded}</strong> ${unit}`;
    }
}

/** Create a unique id */
export function uid(): string {
    return _.uniqueId("uid-");
}

/** Create a time stamp */
export function time(): string {
    const d = new Date();
    const hours = (d.getHours() < 10 ? "0" : "") + d.getHours();
    const minutes = (d.getMinutes() < 10 ? "0" : "") + d.getMinutes();
    return `${d.getDate()}/${d.getMonth() + 1}/${d.getFullYear()}, ${hours}:${minutes}`;
}

/** Append script and style tags to Galaxy main application */
export function appendScriptStyle(data: { script?: string; styles?: string }) {
    // create a script tag inside head tag
    if (data.script && data.script !== "") {
        $("<script/>", { type: "text/javascript" }).text(data.script).appendTo("head");
    }
    // create a style tag inside head tag
    if (data.styles && data.styles !== "") {
        $("<style/>", { type: "text/css" }).text(data.styles).appendTo("head");
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
 * @param {string} str the input value
 * @returns {integer}
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
 * @param selector
 * @returns {Promise<*>}
 */
export async function waitForElementToBePresent(selector: string) {
    while (document.querySelector(selector) === null) {
        await new Promise((resolve) => requestAnimationFrame(resolve));
    }
    return document.querySelector(selector);
}

/**
 * Delays the next operation the specified amount of time.
 * @param {number} delayInMilliseconds The amount of time to wait in milliseconds
 */
export async function delay(delayInMilliseconds: number) {
    if (delayInMilliseconds > 0) {
        await new Promise((r) => setTimeout(r, delayInMilliseconds));
    }
}

export default {
    cssLoadFile: cssLoadFile,
    cssGetAttribute: cssGetAttribute,
    get: get,
    merge: merge,
    bytesToString: bytesToString,
    uid: uid,
    time: time,
    textify: textify,
    isEmpty: isEmpty,
    deepEach: deepEach,
    isJSON: isJSON,
    clone: clone,
    linkify: linkify,
    appendScriptStyle: appendScriptStyle,
    setWindowTitle: setWindowTitle,
    waitForElementToBePresent: waitForElementToBePresent,
    delay: delay,
};
