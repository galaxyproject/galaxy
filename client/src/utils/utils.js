/**
 * Galaxy utilities comprises small functions, which at this point
 * do not require their own classes/files
 */

import _ from "underscore";
import $ from "jquery";
import { getAppRoot } from "onload/loadConfig";
import { getGalaxyInstance } from "app";
import _l from "utils/localization";

/** Builds a basic iframe */
export function iframe(src) {
    return `<iframe src="${src}" frameborder="0" style="width: 100%; height: 100%;"/>`;
}

/** Traverse through json */
export function deepeach(dict, callback) {
    for (var i in dict) {
        var d = dict[i];
        if (_.isObject(d)) {
            var new_dict = callback(d);
            if (new_dict) {
                dict[i] = new_dict;
            }
            deepeach(d, callback);
        }
    }
}

/** Identifies urls and replaces them with anchors */
export function linkify(inputText) {
    var replacedText;
    var replacePattern1;
    var replacePattern2;
    var replacePattern3;

    // URLs starting with http://, https://, or ftp://
    replacePattern1 = /(\b(https?|ftp):\/\/[-A-Z0-9+&@#/%?=~_|!:,.;]*[-A-Z0-9+&@#/%=~_|])/gim;
    replacedText = inputText.replace(replacePattern1, '<a href="$1" target="_blank">$1</a>');

    // URLs starting with "www." (without // before it, or it'd re-link the ones done above).
    replacePattern2 = /(^|[^/])(www\.[\S]+(\b|$))/gim;
    replacedText = replacedText.replace(replacePattern2, '$1<a href="http://$2" target="_blank">$2</a>');

    // Change email addresses to mailto:: links.
    replacePattern3 = /(([a-zA-Z0-9\-_.])+@[a-zA-Z_]+?(\.[a-zA-Z]{2,6})+)/gim;
    replacedText = replacedText.replace(replacePattern3, '<a href="mailto:$1">$1</a>');

    return replacedText;
}

/** Clone */
export function clone(obj) {
    return JSON.parse(JSON.stringify(obj) || null);
}

/**
 * Check if a string is a json string
 * @param{String}   text - Content to be validated
 */
export function isJSON(text) {
    return /^[\],:{}\s]*$/.test(
        text
            .replace(/\\["\\/bfnrtu]/g, "@")
            .replace(/"[^"\\\n\r]*"|true|false|null|-?\d+(?:\.\d*)?(?:[eE][+-]?\d+)?/g, "]")
            .replace(/(?:^|:|,)(?:\s*\[)+/g, "")
    );
}

/**
 * Sanitize/escape a string
 * @param{String}   content - Content to be sanitized
 */
export function sanitize(content) {
    return $("<div/>").text(content).html();
}

/**
 * Checks if a value or list of values is `empty`
 * usually used for selectable options
 * @param{String}   value - Value or list to be validated
 */
export function isEmpty(value) {
    if (!(value instanceof Array)) {
        value = [value];
    }
    if (value.length === 0) {
        return true;
    }
    for (var i in value) {
        if (["__null__", "__undefined__", null, undefined].indexOf(value[i]) > -1) {
            return true;
        }
    }
    return false;
}

/**
 * Convert list to pretty string
 * @param{String}   lst - List of strings to be converted in human readable list sentence
 */
export function textify(lst) {
    if ($.isArray(lst)) {
        lst = lst.toString().replace(/,/g, ", ");
        var pos = lst.lastIndexOf(", ");
        if (pos != -1) {
            lst = `${lst.substr(0, pos)} or ${lst.substr(pos + 2)}`;
        }
        return lst;
    }
    return "";
}

/**
 * Request handler for GET
 * @param{String}   url     - Url request is made to
 * @param{Function} success - Callback on success
 * @param{Function} error   - Callback on error
 * @param{Boolean}  cache   - Use cached data if available
 */
export function get(options) {
    top.__utils__get__ = top.__utils__get__ || {};
    var cache_key = JSON.stringify(options);
    if (options.cache && top.__utils__get__[cache_key]) {
        if (options.success) {
            options.success(top.__utils__get__[cache_key]);
        }
        window.console.debug(`utils.js::get() - Fetching from cache [${options.url}].`);
    } else {
        request({
            url: options.url,
            data: options.data,
            success: function (response) {
                top.__utils__get__[cache_key] = response;
                if (options.success) {
                    options.success(response);
                }
            },
            error: function (response, status) {
                if (options.error) {
                    options.error(response, status);
                }
            },
        });
    }
}

/**
 * Request handler
 * @param{String}   method  - Request method ['GET', 'POST', 'DELETE', 'PUT']
 * @param{String}   url     - Url request is made to
 * @param{Object}   data    - Data send to url
 * @param{Function} success - Callback on success
 * @param{Function} error   - Callback on error
 */
export function request(options) {
    // prepare ajax
    var ajaxConfig = {
        contentType: "application/json",
        type: options.type || "GET",
        data: options.data || {},
        url: options.url,
    };
    // encode data into url
    if (ajaxConfig.type == "GET" || ajaxConfig.type == "DELETE") {
        if (!$.isEmptyObject(ajaxConfig.data)) {
            ajaxConfig.url += ajaxConfig.url.indexOf("?") == -1 ? "?" : "&";
            ajaxConfig.url += $.param(ajaxConfig.data, true);
        }
        ajaxConfig.data = null;
    } else {
        ajaxConfig.dataType = "json";
        ajaxConfig.data = JSON.stringify(ajaxConfig.data);
    }

    // make request
    $.ajax(ajaxConfig)
        .done((response) => {
            if (typeof response === "string") {
                try {
                    response = response.replace("Infinity,", '"Infinity",');
                    response = $.parseJSON(response);
                } catch (e) {
                    console.debug(e);
                }
            }
            if (options.success) {
                options.success(response);
            }
        })
        .fail((response) => {
            var response_text = null;
            try {
                response_text = $.parseJSON(response.responseText);
            } catch (e) {
                response_text = response.responseText;
            }
            if (options.error) {
                options.error(response_text, response.status);
            }
        })
        .always(() => {
            if (options.complete) {
                options.complete();
            }
        });
}

/**
 * Read a property value from CSS
 * @param{String}   classname   - CSS class
 * @param{String}   name        - CSS property
 */
export function cssGetAttribute(classname, name) {
    var el = $(`<div class="${classname}"></div>`);
    el.appendTo(":eq(0)");
    var value = el.css(name);
    el.remove();
    return value;
}

/**
 * Load a CSS file
 * @param{String}   url - Url of CSS file
 */
export function cssLoadFile(url) {
    if (!$(`link[href^="${url}"]`).length) {
        $(`<link href="${getAppRoot()}${url}" rel="stylesheet">`).appendTo("head");
    }
}

/**
 * Safely merge to dictionaries
 * @param{Object}   options         - Target dictionary
 * @param{Object}   optionsDefault  - Source dictionary
 */
export function merge(options, optionsDefault) {
    if (options) {
        return _.defaults(options, optionsDefault);
    } else {
        return optionsDefault;
    }
}

/**
 * Round floaing point 'number' to 'numPlaces' number of decimal places.
 * @param{Object}   number      a floaing point number
 * @param{Object}   numPlaces   number of decimal places
 */
export function roundToDecimalPlaces(number, numPlaces) {
    var placesMultiplier = 1;
    for (var i = 0; i < numPlaces; i++) {
        placesMultiplier *= 10;
    }
    return Math.round(number * placesMultiplier) / placesMultiplier;
}

// calculate on import
var kb = 1024;
var mb = kb * kb;
var gb = mb * kb;
var tb = gb * kb;

/**
 * Format byte size to string with units
 * @param{Integer}   size           - Size in bytes
 * @param{Boolean}   normal_font    - Switches font between normal and bold
 */
export function bytesToString(size, normal_font, numberPlaces) {
    numberPlaces = numberPlaces !== undefined ? numberPlaces : 1;
    // identify unit
    var unit = "";
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
    var rounded = unit == "b" ? size : roundToDecimalPlaces(size, numberPlaces);
    if (normal_font) {
        return `${rounded} ${unit}`;
    } else {
        return `<strong>${rounded}</strong> ${unit}`;
    }
}

/** Create a unique id */
export function uid() {
    top.__utils__uid__ = top.__utils__uid__ || 0;
    return `uid-${top.__utils__uid__++}`;
}

/** Create a time stamp */
export function time() {
    var d = new Date();
    var hours = (d.getHours() < 10 ? "0" : "") + d.getHours();
    var minutes = (d.getMinutes() < 10 ? "0" : "") + d.getMinutes();
    return `${d.getDate()}/${d.getMonth() + 1}/${d.getFullYear()}, ${hours}:${minutes}`;
}

/** Append script and style tags to Galaxy main application */
export function appendScriptStyle(data) {
    // create a script tag inside head tag
    if (data.script && data.script !== "") {
        $("<script/>", { type: "text/javascript" }).text(data.script).appendTo("head");
    }
    // create a style tag inside head tag
    if (data.styles && data.styles !== "") {
        $("<style/>", { type: "text/css" }).text(data.styles).appendTo("head");
    }
}

/** Get querystrings from url */
export function getQueryString(key) {
    return decodeURIComponent(
        window.location.search.replace(
            new RegExp(`^(?:.*[&\\?]${encodeURIComponent(key).replace(/[.+*]/g, "\\$&")}(?:\\=([^&]*))?)?.*$`, "i"),
            "$1"
        )
    );
}

export function setWindowTitle(title) {
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
export function hashFnv32a(str) {
    var i;
    var l;
    var hval = 0x811c9dc5;

    for (i = 0, l = str.length; i < l; i++) {
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
export async function waitForElementToBePresent(selector) {
    while (document.querySelector(selector) === null) {
        await new Promise((resolve) => requestAnimationFrame(resolve));
    }
    return document.querySelector(selector);
}

/**
 * Delays the next operation the specified amount of time.
 * @param {Number} delayInMilliseconds The amount of time to wait in milliseconds
 */
export async function delay(delayInMilliseconds) {
    if (delayInMilliseconds > 0) {
        await new Promise((r) => setTimeout(r, delayInMilliseconds));
    }
}

export default {
    cssLoadFile: cssLoadFile,
    cssGetAttribute: cssGetAttribute,
    get: get,
    merge: merge,
    iframe: iframe,
    bytesToString: bytesToString,
    uid: uid,
    time: time,
    request: request,
    sanitize: sanitize,
    textify: textify,
    isEmpty: isEmpty,
    deepeach: deepeach,
    isJSON: isJSON,
    clone: clone,
    linkify: linkify,
    appendScriptStyle: appendScriptStyle,
    getQueryString: getQueryString,
    setWindowTitle: setWindowTitle,
    waitForElementToBePresent: waitForElementToBePresent,
    delay: delay,
};
