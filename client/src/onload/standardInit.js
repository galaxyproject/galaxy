import galaxyModule from "@/app/galaxy";
import { getGalaxyInstance, setGalaxyInstance } from "@/app/singleton";

import { initSentry } from "./globalInits/initSentry";
import { onloadWebhooks } from "./globalInits/onloadWebhooks";
import { loadConfig } from "./loadConfig";

const { GalaxyApp } = galaxyModule;

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

    // Initialize globals
    await initSentry(app, config);
    await onloadWebhooks(app);

    // Initialization complete
    console.debug(`${label} app`);
    return app;
}
