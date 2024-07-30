import createClient from "openapi-fetch";

import { getAppRoot } from "@/onload/loadConfig";

import { type components, type paths as GalaxyApiPaths } from "./schema";

export { type components, type GalaxyApiPaths };

export const client = createClient<GalaxyApiPaths>({ baseUrl: getAppRoot(undefined, true) });
