/**
 * TODO: Make this part of galaxy.js later, once the global refs are gone
 */

import config from "config";
import { GalaxyApp } from "./galaxy";
import { serverPath } from "utils/serverPath";

export function setGalaxyInstance(factory) {
    if (!config.testBuild === true) {
        console.warn("setGalaxyInstance", serverPath());
    }

    const storage = getStorage();
    let newInstance = factory(GalaxyApp);
    if (!(newInstance instanceof GalaxyApp)) {
        newInstance = new GalaxyApp(newInstance);
    }

    storage._galaxyInstance = newInstance;

    return storage._galaxyInstance;
}

export function getGalaxyInstance() {
    const storage = getStorage();
    return storage._galaxyInstance;
}

export function galaxyIsInitialized() {
    const instance = getGalaxyInstance();
    return instance !== null;
}

// Having a CORS issue in the toolshed iframe, store separate versions
// of galaxy in each window for the short-term
export function getStorage() {
    return window;
}
