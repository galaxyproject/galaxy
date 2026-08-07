// index.ts
import "bootstrap";
import "@/style/scss/base.scss";
// Default Font
import "@fontsource/atkinson-hyperlegible";
import "@fontsource/atkinson-hyperlegible/700.css";
// Galaxy brand design tokens (shared with the Galaxy Hub and IWC)
import "@galaxyproject/brand-tokens/tokens.css";

import config from "config";

import { overrideProductionConsole } from "./console";
import { getAppRoot, loadConfig } from "./loadConfig";

overrideProductionConsole();

export { getAppRoot, loadConfig };

if (!config.testBuild) {
    console.log(`Galaxy Client '${config.name}' build, dated ${config.buildTimestamp}`);
    console.debug("Full environment configuration:", config);
}
