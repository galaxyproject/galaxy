/**
 * Diagnostic utility, can be setup to monitor globally assigned resources. For
 * instance if some legacy script set a variable called window.Bob, call
 * installMonitor("Bob"). Then open the chrome console and type
 * toggleGlobalMonitor("Bob", true) to receive console.log messages and a
 * traceroute every time some random script accesses window.Bob or one of its
 * properties.
 */

import { mock } from "utils/mock";

// stores values that are returned when somebody asks for window.Something
window._monitorStorage = window._monitorStorage || {};

export function installMonitor(globalProp) {
    // Need to handle the special case of window.Galaxy because
    // we already install an Object.defineProperty on window.Galaxy
    // to make the singleton available to legacy scripts
    if (globalProp == "Galaxy") {
        // handled in singleton
        return;
    }

    // watch window.globalProp as a whole with a Object.defineProperty
    installObjectWatcher(globalProp);
}

export function installObjectWatcher(globalProp, getter = null, setter = null) {
    const label = `window.${globalProp}`;
    const debug = isPropMonitored(globalProp);
    const logger = debug ? console : mock(console);

    // Replaces window.Thing with an object definition that forwards
    // gets and set values to window._monitorStorage

    Object.defineProperty(window, globalProp, {
        enumerable: true,
        configurable: false,
        get() {
            let val = undefined;
            logger.groupCollapsed(`${label} read`);
            logger.trace();
            try {
                if (getter) {
                    val = getter();
                } else {
                    val = window._monitorStorage[globalProp];
                }
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
                if (setter) {
                    setter(newValue);
                } else {
                    window._monitorStorage[globalProp] = newValue;
                }
            } catch (err) {
                logger.log("Unable to set value on window facade");
                logger.warn(err);
            }
            logger.groupEnd();
        },
    });
}

// sets a flag in sessionStorage to install a monitor for the
// indicated prop on the next page refresh
export function toggleGlobalMonitor(prop, bShow = true) {
    const toggleList = getToggles();
    if (bShow) {
        toggleList[prop] = true;
    } else {
        if (prop in toggleList) {
            delete toggleList[prop];
        }
    }
    setToggles(toggleList);
    return toggleList;
}

// determines whether specified prop is toggled on or off by the user
export function isPropMonitored(prop) {
    const toggleList = getToggles();
    return toggleList[prop] == true;
}

// show list of monitor toggles
export function showMonitorToggles() {
    const toggleList = getToggles();
    console.log(toggleList);
}

// retrieve toggle list from the session storage
function getToggles() {
    const json = sessionStorage.getItem("global_monitors");
    return json ? JSON.parse(json) : {};
}

// put the toggle list back in session storage
function setToggles(toggleList) {
    sessionStorage.setItem("global_monitors", JSON.stringify(toggleList));
}

// Display properties available for monitoring at time of page reload
// (you can add more during a page-session with installMonitor)
export function monitorInit() {
    const monitoredProps = Object.keys(getToggles());

    console.groupCollapsed("monitor init");
    console.log(
        "The following global properties are monitored because they were setup in the javascript source manually:",
        monitoredProps
    );
    console.log("To toggle messages on/off, type toggleGlobalMonitor('Galaxy', true|false) into the console");
    console.log("You can set up any other variable by typing installMonitor('a window variable name')");
    console.groupEnd();

    // installs monitors from stored list
    monitoredProps.forEach(installMonitor);

    // makes monitor installation available at console
    window.installMonitor = installMonitor;

    // Type showMonitoredProperties in developer console to list which
    // global variables have actually been proxied
    window.showMonitorToggles = showMonitorToggles;

    // Type toggleGlobalMonitor("variableName", true|false) in
    // the developer console to enable/disable
    window.toggleGlobalMonitor = toggleGlobalMonitor;
}
