// Galaxy.data.dialog mounts DataDialog, which needs the same compat config as
// the analysis app; without it compat runs everything on its defaults.
import "@/compat-config";

import { initGalaxyInstance } from "@/app";
import { onDomReady } from "@/utils/onDomReady";

onDomReady(async () => {
    await initGalaxyInstance();
});
