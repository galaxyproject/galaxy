import { initGalaxyInstance } from "@/app";
import * as bundleEntries from "@/bundleEntries";
import * as config from "@/onload/loadConfig";

// Expose bundleEntries and config to window for Mako templates
window.bundleEntries = bundleEntries;
window.config = config;

window.addEventListener("load", async () => {
    await initGalaxyInstance();
});
