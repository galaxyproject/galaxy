// Initializes "training wheels" causing legacy references to window.Galaxy to
// pass through the singleton accessors. All future code should access galaxy
// through getGalaxyInstance, and rarely with setGalaxyInstance

import { getGalaxyInstance, setGalaxyInstance } from "app";
import { getAppRoot } from "onload/loadConfig";
import { serverPath } from "utils/serverPath";
import config from "config";

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
            return getGalaxyInstance() || galaxyStub;
        },
        set: function (newValue) {
            console.warn("accessing (set) window.Galaxy", serverPath());
            setGalaxyInstance(newValue);
        },
    });
} else {
    console.error("Detected redefinition of window.Galaxy -- skipping, but this should be investigated.", serverPath());
}

export default window.Galaxy;
