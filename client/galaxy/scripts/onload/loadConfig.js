/**
 * Exposes the global configuration variable via a config.set function which is
 * exposed to the python templates. Or, you can just import the functions and
 * use them inside webpack-generated code. The idea is that we provide an
 * observable that debounces changes and avoids instantiating a Galaxy app until
 * values stop getting merged into the config.
 *
 * To set custom configuration variables from python just use something like:
 *      config.set({
 *          abc: {
 *              thing: "doodah"
 *          }
 *      });
 *
 * inside a python template to append new properties to the global config before
 * it is passed to the GalaxyApp constructor
 *
 * This alleviates some of the timing headaches caused by python printing out
 * script tags in the HTML body, or loading new config information inside of
 * iframes, etc.
 */

import { BehaviorSubject, Subject } from "rxjs";
import { debounceTime, scan, filter } from "rxjs/operators";
import { getRootFromIndexLink } from "./getRootFromIndexLink";
import { defaultConfigs } from "./defaultConfigs";

// exporting this addInitialization to window.config variable
export { addInitialization } from "./initQueue";

// Config observable

// Process incoming config.set valls
const input = new Subject();
const mergedConfigs = input.pipe(
    filter(fragment => fragment instanceof Object),
    scan((config, fragment) => {
        return Object.assign({}, config, fragment);
    }, defaultConfigs)
);

// keep running config value
const currentConfig$ = new BehaviorSubject(defaultConfigs);
mergedConfigs.subscribe(currentConfig$);

// debounce, filter out initial null and other invalid stuff
export const config$ = currentConfig$.asObservable().pipe(
    filter(Boolean),
    debounceTime(100)
);

/**
 * Adds config objects into the global configuration.
 * @param  {...objects} fragments Config objects to be merged into the global config
 */
export function set(...fragments) {
    fragments.forEach(fragment => input.next(fragment));
}

/**
 * Retrieves current value of the configuration, used for legacy code.
 */
export function get() {
    return currentConfig$.getValue();
}

/**
 * A lot of backbone objects are accessing window.Galaxy purely to get this
 * value which is problematic since they execute as soon as the scripts hit the
 * page.
 *
 * @param {*} defaultRoot
 */
export function getAppRoot(defaultRoot = "/") {
    let root = defaultRoot;
    try {
        // try actual config
        root = get().options.root;
    } catch (err) {
        try {
            root = getRootFromIndexLink(defaultRoot);
        } catch (err) {
            console.warn("Unable to find index link in head", err);
        }
    }
    return root;
}
