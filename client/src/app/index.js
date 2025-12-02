import { GalaxyApp } from "@/app/galaxy";
import { loadConfig } from "@/onload/loadConfig";

export function getGalaxyInstance() {
    return window._galaxyInstance;
}

export function setGalaxyInstance(instance) {
    if (!(instance instanceof GalaxyApp)) {
        throw new Error("Expected GalaxyApp instance.");
    }
    window._galaxyInstance = instance;
    return instance;
}

export async function initGalaxyInstance() {
    const config = await loadConfig();
    const app = new GalaxyApp(config, {});
    setGalaxyInstance(app);

    if (!window.Galaxy) {
        Object.defineProperty(window, "Galaxy", {
            enumerable: true,
            configurable: true,
            get: getGalaxyInstance,
        });
    }

    return app;
}
