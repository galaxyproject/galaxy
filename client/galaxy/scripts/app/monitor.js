// Initializes "training wheels" causing legacy references to window.Galaxy to
// pass through the singleton accessors. All future code should access galaxy
// through getGalaxyInstance, and rarely with setGalaxyInstance

import { getGalaxyInstance, setGalaxyInstance } from "app";
import { getAppRoot } from "onload/loadConfig";
import { serverPath } from "utils/serverPath";

const galaxyStub = {
    root: getAppRoot(),
    config: {}
};

Object.defineProperty(window, "Galaxy", {
    enumerable: true,
    get: function() {
        console.warn("accessing (get) window.Galaxy", serverPath());
        return getGalaxyInstance() || galaxyStub;
    },
    set: function(newValue) {
        console.warn("accessing (set) window.Galaxy", serverPath());
        setGalaxyInstance(newValue);
    }
});

export default window.Galaxy;

