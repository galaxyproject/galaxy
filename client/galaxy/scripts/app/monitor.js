import { installMonitor } from "utils/installMonitor";
import { getGalaxyInstance, setGalaxyInstance } from "app";
import { getAppRoot } from "onload/loadConfig";

let proxy;

const galaxyStub = {
    root: getAppRoot(),
    config: {}
};

if (!proxy) {
    
    // force references to window.galaxy to pass through the set/get instance functions
    // The monitor is going to store Galaxy at window._monitorStorage["Galaxy"]
    Object.defineProperty(window._monitorStorage, "Galaxy", {
        enumerable: true,
        configurable: false,
        get: getGalaxyInstance,
        set: (newValue) => setGalaxyInstance(() => newValue)
    });
    
    let existingGalaxy = getGalaxyInstance();
    proxy = installMonitor("Galaxy", existingGalaxy || galaxyStub);
}

export default proxy;
