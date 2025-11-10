// index.ts
import "bootstrap";
import "@/style/scss/base.scss";
import "./publicPath";
import "@fontsource/atkinson-hyperlegible";
import "@fontsource/atkinson-hyperlegible/700.css";

import config from "config";

import { overrideProductionConsole } from "./console";
import { getRootFromIndexLink } from "./getRootFromIndexLink";
import { getAppRoot, getConfig, loadConfig } from "./loadConfig";
import { standardInit } from "./standardInit";

overrideProductionConsole();

export { getAppRoot, getConfig, getRootFromIndexLink, loadConfig, standardInit };

if (!config.testBuild) {
    console.log(`Galaxy Client '${config.name}' build, dated ${config.buildTimestamp}`);
    console.debug("Full environment configuration:", config);
}
