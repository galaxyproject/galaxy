import { GalaxyApp } from "@/app/galaxy";
import { getGalaxyInstance, setGalaxyInstance } from "@/app/singleton";

import { loadConfig } from "./loadConfig";

export async function standardInit(label = "Galaxy") {
    const config = await loadConfig();
    const app = new GalaxyApp(config, {});

    // Register singleton
    setGalaxyInstance(() => app);

    // Expose Galaxy object in window
    if (!window.Galaxy) {
        Object.defineProperty(window, "Galaxy", {
            enumerable: true,
            configurable: true,
            get: () => getGalaxyInstance(),
        });
    }

    // Initialization complete
    console.debug(`${label} app`);
    return app;
}
