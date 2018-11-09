/**
 * Diagnostic utility, can be setup to monitor globally assigned resources. For
 * instance if some legacy script set a variable called window.Bob, call
 * installMonitor("Bob"). Then open the chrome console and type
 * toggleGlobalMonitor("Bob", true) to receive console.log messages and a
 * traceroute every time some random script accesses window.Bob or one of its
 * properties.
 */

import { mock } from "utils/mock";
import store from "store";
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
    logger.groupCollapsed(`${label} populating monitor storage with initial value`);
    logger.log(existingValue);
    logger.groupEnd();

    // Replaces window.Thing with an object definition that forwards
    // gets and set values to window._monitorStorage
    try {
        Object.defineProperty(window, globalProp, {
            enumerable: true,
            configurable: false,
            get() {
                let val = undefined;
                logger.groupCollapsed(`${label} read`);
                logger.trace();
                try {
                    val = window._monitorStorage[globalProp];
                    logger.log(val);
                } catch (err) {
                    logger.warn("Unable to retrieve");
                    logger.warn(err);
                }
                logger.groupEnd();
                return val;
            },
            set(newValue) {
                logger.groupCollapsed(`${label} write...`, String(newValue));
                logger.trace();
                try {
                    window._monitorStorage[globalProp] = newValue;
                } catch(err) {
                    logger.log("Unable to set value on window facade");
                    logger.warn(err);
                }
                logger.groupEnd();
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
                let val = undefined;
                logger.groupCollapsed(`${label}.${prop} read`);
                logger.trace();
                try {
                    let target = window[globalProp];
                    val = target[prop];
                } catch (err) {
                    logger.warn("Unable to retrieve property from proxy", prop);
                    logger.warn(err);
                }
                logger.groupEnd();
                return val;
            },
            set(o, prop, val) {
                let didWrite = true;
                logger.groupCollapsed(`${label}.${prop} write`);
                logger.trace();
                try {
                    let target = window[globalProp];
                    logger.log("new value", String(val));
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
    let toggleList = getToggles();
    toggleList[prop] = Boolean(bShow);
    setToggles(toggleList);
    return toggleList;
}

// determines whether specified prop is toggled on or off by the user
export function isPropMonitored(prop) {
    let toggleList = getToggles();
    return toggleList[prop] == true;
}

function getToggles() {
    let json = store.get("global_monitors");
    let existinglist = json ? JSON.parse(json) : {};
    return existinglist;
}

function setToggles(toggleList) {
    store.set("global_monitors", JSON.stringify(toggleList));
}

// Console utilities

// Type showMonitoredProperties in developer console to list which
// global variables have actually been proxied
window.showMonitoredProperties = showMonitoredProperties;

// Type toggleGlobalMonitor("variableName", true|false) in
// the developer console to enable/disable
window.toggleGlobalMonitor = toggleGlobalMonitor;
