import createClient from "openapi-fetch";

import { type GalaxyApiPaths } from "@/api/schema";
import { getAppRoot } from "@/onload/loadConfig";

function createApiClient() {
    return createClient<GalaxyApiPaths>({ baseUrl: getAppRoot(undefined, true) });
}

let client: ReturnType<typeof createApiClient>;

export function useClientApi() {
    if (!client) {
        client = createApiClient();
    }

    return { client };
}
