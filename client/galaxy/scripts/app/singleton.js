/**
 * TODO: Make this part of galaxy.js later, once the global refs are gone
 */

import addLogging from "utils/add-logging";
import { GalaxyApp } from "./galaxy";
import { serverPath } from "utils/serverPath";
import { getAppRoot } from "onload";
import { installObjectWatcher } from "utils/installMonitor";

const galaxyStub = {
    root: getAppRoot(),
    config: {}
};

// Causes global Galaxy references to pass through the singleton functions
installObjectWatcher("Galaxy", getGalaxyInstance, (newValue) => {
    return setGalaxyInstance(() => newValue);
});

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
    if ("_galaxyInstance" in storage) {
        return storage._galaxyInstance;
    }
    return Object.assign({}, galaxyStub);
}

export function getStorage() {
    return window.top;
}
