/**
 * TODO: Make this part of galaxy.js later, once the global refs are gone
 *
 * DO NOT import GalaxyApp into this file or you will create a catch-22 circular
 * dependency situation with the galaxy.monitor as window.Galaxy refers to the
 * instance and the instance refers to hard-coded Galaxy config variables which
 * refer back to window.Galaxy
 */

import addLogging from "utils/add-logging";
import { GalaxyApp } from "./galaxy";
import { serverPath } from "utils/serverPath";

export function setGalaxyInstance(factory, atTop = true) {
    // console.warn("setGalaxyInstance", serverPath());

    let storage = getStorage(atTop);
    let newInstance = factory(GalaxyApp);
    
    if (newInstance.constructor.name != "GalaxyApp") {
        newInstance = new GalaxyApp(newInstance);
    }
    if (newInstance.debug === undefined) {
        addLogging(newInstance, "GalaxyApp");
    }

    // Debugging frame property
    
    // storage._galaxyInstance = new Proxy(newInstance, {
    //     get(galaxy, prop) {
    //         if (prop == "frame") {
    //             console.groupCollapsed("Frame Get", serverPath());
    //             console.trace();
    //             console.groupEnd();
    //         }
    //         return galaxy[prop];
    //     },
    //     set(galaxy, prop, val) {
    //         galaxy[prop] = val;
    //         if (prop == "frame") {
    //             console.groupCollapsed("Frame Set", serverPath());
    //             console.log(val);
    //             console.trace();
    //             console.groupEnd();
    //         }
    //         return true;
    //     }
    // });

    storage._galaxyInstance = newInstance;

    return storage._galaxyInstance;
}

export function getGalaxyInstance(atTop = true) {
    let storage = getStorage(atTop);
    return storage._galaxyInstance;
}

export function galaxyIsInitialized(atTop = true) {
    let instance = getGalaxyInstance(atTop);
    return instance !== null;
}

export function getStorage(atTop = true) {
    let storage = ((window !== window.top) && atTop) ? window.top : window;
    return storage;
}
