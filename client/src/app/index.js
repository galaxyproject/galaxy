import { GalaxyApp } from "@/app/galaxy";
import { getGalaxyInstance, setGalaxyInstance } from "@/app/singleton";
import { loadConfig } from "@/onload/loadConfig";

export { getGalaxyInstance, setGalaxyInstance };

export async function initGalaxyInstance() {
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

    return app;
}
