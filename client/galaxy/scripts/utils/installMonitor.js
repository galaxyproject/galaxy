/**
 * Diagnostic utility, can be setup to monitor globally assigned resources. For
 * instance if some legacy script set a variable called window.Bob, call
 * installMonitor("Bob"). Then open the chrome console and type
 * toggleGlobalMonitor("Bob", true) to receive console.log messages and a
 * traceroute every time some random script accesses window.Bob or one of its
 * properties.
 */

import { mock } from "utils/mock";
const fakeLogger = mock(console);

// stores values that are returned when somebody asks for window.Something
window._monitorStorage = window._monitorStorage || {};

export function installMonitor(globalProp, fallbackValue) {
    let label = `window.${globalProp}`;
    let debug = isPropMonitored(globalProp);
    let logger = debug ? console : fakeLogger;

    // initialize storage with existing value
    let existingValue = window[globalProp] || fallbackValue;
    window._monitorStorage[globalProp] = existingValue;
    logger.log(label, "Populating storage with initial value", existingValue);

    // Replaces window.Thing with an object definition that forwards
    // gets and set values to window._monitorStorage
    try {
        Object.defineProperty(window, globalProp, {
            enumerable: true,
            configurable: false,
            get() {
                try {
                    let val = window._monitorStorage[globalProp];
                    logger.groupCollapsed(`${label} read`);
                    logger.log(val);
                    logger.trace();
                    logger.groupEnd();
                    return val;
                } catch (err) {
                    logger.warn("Unable to retrieve", globalProp, err);
                }
                return null;
            },
            set(newValue) {
                logger.groupCollapsed(`${label} write...`, newValue);
                logger.trace();
                logger.groupEnd();
                window._monitorStorage[globalProp] = newValue;
            }
        });
    } catch (err) {
        logger.warn("Unable to install facade", err);
    }

    // Proxies the above object definition so we can watch changes to
    // that object's properties (i.e. window.Thing.prop = "abc")

    return new Proxy(
        {},
        {
            get(o, prop) {
                let target = window[globalProp];
                try {
                    logger.groupCollapsed(`${label}.${prop} read`);
                    logger.trace();
                    logger.groupEnd();
                    let val = target[prop];
                    return val;
                } catch (err) {
                    console.log("Unable to retrieve property from proxy", err, target, globalProp)
                    return undefined;
                }
            },
            set(o, prop, val) {
                let didWrite = true;
                let target = window[globalProp];
                logger.groupCollapsed(`${label}.${prop} write`, typeof(val));
                try {
                    logger.log("new value", val);
                    logger.trace();
                    target[prop] = val;
                } catch(err) {
                    logger.warn("Unable to write", globalProp, val);
                    didWrite = false;
                }
                logger.groupEnd();
                return didWrite;
            }
        }
    );
}

// Shows which properties are actually being monitored
export function showMonitoredProperties() {
    return Object.keys(window._monitorStorage);
}

// sets a flag in sessionStorage to install a monitor for the
// indicated prop on the next page refresh

export function toggleGlobalMonitor(prop, bShow = false) {
    let toggleList = getSessionToggles();
    toggleList[prop] = Boolean(bShow);
    setSessionToggles(toggleList);
    return toggleList;
}

// determines whether specified prop is toggled on or off by the user
export function isPropMonitored(prop) {
    let toggleList = getSessionToggles();
    return toggleList[prop] == true;
}

function getSessionToggles() {
    let json = sessionStorage.getItem("global_monitors");
    let existinglist = json ? JSON.parse(json) : {};
    return existinglist;
}

function setSessionToggles(toggleList) {
    sessionStorage.setItem("global_monitors", JSON.stringify(toggleList));
}

// Console utilities

// Type showMonitoredProperties in developer console to list which
// global variables have actually been proxied
window.showMonitoredProperties = showMonitoredProperties;

// Type toggleGlobalMonitor("variableName", true|false) in
// the developer console to enable/disable
window.toggleGlobalMonitor = toggleGlobalMonitor;
