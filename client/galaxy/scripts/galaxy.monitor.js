import { installMonitor } from "utils/installMonitor";
import { getGalaxyInstance, setGalaxyInstance } from "galaxy.singleton";
import { getAppRoot } from "onload/loadConfig";
import { serverPath } from "utils/serverPath";

let proxy;

if (proxy) {
    console.log("window proxy already defined");
    debugger;
}

if (!proxy) {

    console.log("Initializing default galaxy object", serverPath(window.location.href));

    setGalaxyInstance(() => ({
        root: getAppRoot(),
        config: {}
    }));

    Object.defineProperty(window._monitorStorage, "Galaxy", {
        enumerable: true,
        configurable: false,
        get() {
            return getGalaxyInstance();
        },
        set(newValue) {
            setGalaxyInstance(() => newValue);
        }
    });

    proxy = installMonitor("Galaxy");
}

export default proxy;
