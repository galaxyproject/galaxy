/**
 * Exported objects here are available in window scope on the
 * python templates for purposes of initializination.
 * 
 * Called by python templates to setup configuration variables.
 * Intermediate step to complete removal of python templates.
 */

import { BehaviorSubject } from "rxjs";
import { debounceTime } from "rxjs/operators";
import { serverPath } from "utils/serverPath";

export { addInitialization } from "./initQueue";

const defaultConfigs = {
    options: {
        root: getRootFromIndexLink()
    },
    bootstrapped: {},
    form_input_auto_focus: false,
    sentry: {}
};

// Config observable
const configStorage = new BehaviorSubject(defaultConfigs);

export const config$ = configStorage.pipe(
    debounceTime(50)
);

// Allow templates to set config vars
export function setConfig(...fragments) {
    // console.log("setConfig", ...fragments);
    fragments = fragments.filter(fragment => fragment instanceof Object);
    if (fragments.length == 0) {
        return;
    }
    try {
        let newConfig = Object.assign({}, configStorage.getValue(), ...fragments);
        configStorage.next(newConfig);
    } catch(err) {
        console.warn("setConfig error");
        console.dir(fragments);
        console.log("unable to assign configs");
        console.error(err);
    }
}

// Retrieves current value of the configuration observable
// Used for synchronous legacy code when there's no other option
export function getConfig() {
    return config$.getValue();
}

export function getAppRoot(defaultRoot = "/") {
    let root = defaultRoot;
    try {
        // try actual config
        root = getConfig().options.root;
    } catch (err) {
        try {
            root = getRootFromIndexLink(defaultRoot);
        } catch (err) {
            console.warn("Unable to find index link in head", err);
        }
    }
    return root;
}

// Finds <link rel="index"> in head element and pulls root url fragment from
// there That should probably have been a <base> tag instead since that's how
// they're using <link rel="index" />, but why should we expect modern web
// developers to understand HTML 1.0?
function getRootFromIndexLink(defaultRoot = "/") {
    let links = document.getElementsByTagName("link");
    let indexLink = [...links].find(link => link.rel == "index");
    if (indexLink && indexLink.href) {
        return serverPath(indexLink.href);
    }
    return defaultRoot;
}
