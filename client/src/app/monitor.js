// Initializes "training wheels" causing legacy references to window.Galaxy to
// pass through the singleton accessors. All future code should access galaxy
// through getGalaxyInstance, and rarely with setGalaxyInstance

import { getGalaxyInstance, setGalaxyInstance } from "app";
import config from "config";
import { getAppRoot } from "onload/loadConfig";
import { serverPath } from "utils/serverPath";

const galaxyStub = {
    root: getAppRoot(),
    config: {},
};

if (!window.Galaxy) {
    Object.defineProperty(window, "Galaxy", {
        enumerable: true,
        get: function () {
            if (!config.testBuild === true) {
                console.warn("accessing (get) window.Galaxy", serverPath());
            }
            return (getGalaxyInstance && getGalaxyInstance()) || galaxyStub;
        },
        set: function (newValue) {
            console.warn("accessing (set) window.Galaxy", serverPath());
            setGalaxyInstance(newValue);
        },
    });
} else {
    if (process.env.NODE_ENV != "test") {
        console.debug("Skipping, window.Galaxy already exists.", serverPath());
    }
}

export default window.Galaxy;
