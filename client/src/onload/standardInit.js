// standardInit.ts
import galaxyModule from "@/app/galaxy";
import { setGalaxyInstance } from "@/app/singleton";

import { globalInits } from "./globalInits";
import { loadConfig } from "./loadConfig";

const { GalaxyApp } = galaxyModule;

export async function standardInit(label = "Galaxy") {
    const config = await loadConfig();
    const app = new GalaxyApp(config, {});
    setGalaxyInstance(() => app);
    console.debug(`${label} app`);
    await globalInits(app, config);
    return app;
}
