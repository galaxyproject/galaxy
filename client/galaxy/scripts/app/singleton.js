/**
 * TODO: Make this part of galaxy.js later, once the global refs are gone
 */

import addLogging from "utils/add-logging";
import { GalaxyApp } from "./galaxy";
import { serverPath } from "utils/serverPath";

export function setGalaxyInstance(factory) {
    console.warn("setGalaxyInstance", serverPath());

    let storage = getStorage();
    let newInstance = factory(GalaxyApp);
    if (!(newInstance instanceof GalaxyApp)) {
        newInstance = new GalaxyApp(newInstance);
    }
    if (newInstance.debug === undefined) {
        addLogging(newInstance, "GalaxyApp");
    }

    storage._galaxyInstance = newInstance;

    return storage._galaxyInstance;
}

export function getGalaxyInstance() {
    let storage = getStorage();
    return storage._galaxyInstance;
}

export function galaxyIsInitialized() {
    let instance = getGalaxyInstance();
    return instance !== null;
}

// Having a CORS issue in the toolshed iframe, store separate versions
// of galaxy in each window for the short-term
export function getStorage() {
    return window;
}
