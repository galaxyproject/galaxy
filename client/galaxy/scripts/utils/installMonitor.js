/**
 * Diagnostic utility, can be setup to monitor globally assigned resources. For
 * instance if some legacy script set a variable called window.Bob, call
 * installMonitor("Bob"). Then open the chrome console and type
 * toggleMonitorMessages("Bob", true) to receive console.log messages and a
 * traceroute every time some random script actually accesses window.Bob.
 */

import { mock } from "utils/mock";

const fakeLogger = mock(console);

// stores values that are returned when somebody asks for window.Something
window._monitorStorage = {};

export function installMonitor(globalProp, fallbackValue = null) {

    let label = `window.${globalProp}`;
    let debug = getMonitorToggle(globalProp);
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
                } catch(err) {
                    logger.warn("Unable to retrieve", globalProp, err);
                }
                return null;
            },
            set(newValue) {
                logger.groupCollapsed(`${label} write...`, newValue);
                logger.trace();
                logger.groupEnd();
                return window._monitorStorage[globalProp] = newValue;
            }
        });
    } catch (err) {
        logger.warn("Unable to install facade", err);
    }

    // Proxies the above object definition so we can watch changes to
    // that object's properties (i.e. window.Thing.prop = "abc")
    
    return new Proxy({}, {
        get(o, prop) {
            logger.groupCollapsed(`${label}.${prop} read`);
            let target = window[globalProp];
            logger.log("o?", o);
            logger.log("target?", target);
            logger.trace();
            logger.groupEnd();
            let val = target[prop];
            return val;
        },
        set(o, prop, val) {
            let target = window[globalProp];
            logger.groupCollapsed(`${label}.${prop} write`, val);
            logger.log("o?", o);
            logger.log("target?", target);
            logger.trace();
            logger.groupEnd();
            return (target[prop] = val);
        }
    });
}


// Shows a list of all monitored properties

export function showMonitoredProperties() {
    return Object.keys(window._monitorStorage);
}


// Message Toggles

export function toggleMonitorMessages(prop, bShow = false) {
    sessionStorage.setItem(sessionKey(prop), Boolean(bShow));
}

function sessionKey(prop) {
    return `monitor_debug_${prop}`;
}

function getMonitorToggle(prop) {
    let toggle = sessionStorage.getItem(sessionKey(prop));
    return (toggle == "true");
}



// Console utilities

// showMonitoredProperties() in console to list all
// currently monitored properties

window.showMonitoredProperties = showMonitoredProperties;

// Type toggleMonitorMessages("variableName", true|false) in
// the developer console to enable/disable

window.toggleMonitorMessages = toggleMonitorMessages;
