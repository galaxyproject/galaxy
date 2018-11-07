import { installMonitor } from "utils/installMonitor";
import { getGalaxyInstance, setGalaxyInstance } from "galaxy.singleton";
import { getAppRoot } from "onload/loadConfig";
// import { serverPath } from "utils/serverPath";

let proxy;

const galaxyStub = {
    root: getAppRoot(),
    config: {}
};

if (!proxy) {

    // console.log("Initializing default galaxy object", serverPath(window.location.href));

    // force references to window.galaxy to pass through the set/get instance functions
    // The monitor is going to store Galaxy at window._monitorStorage["Galaxy"]
    Object.defineProperty(window._monitorStorage, "Galaxy", {
        enumerable: true,
        configurable: false,
        get: getGalaxyInstance,
        set: (newValue) => setGalaxyInstance(() => newValue)
    });

    proxy = installMonitor("Galaxy", galaxyStub);
}

export default proxy;
