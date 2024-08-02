import createClient from "openapi-fetch";

import { type GalaxyApiPaths } from "@/api/schema";
import { getAppRoot } from "@/onload/loadConfig";

function getBaseUrl() {
    const isTest = process.env.NODE_ENV === "test";
    return isTest ? window.location.origin : getAppRoot(undefined, true);
}

function createApiClient() {
    return createClient<GalaxyApiPaths>({ baseUrl: getBaseUrl() });
}

export type GalaxyApiClient = ReturnType<typeof createApiClient>;

let client: GalaxyApiClient;

/**
 * Returns the Galaxy API client.
 *
 * It can be used to make requests to the Galaxy API using the OpenAPI schema.
 */
export function GalaxyApi(): GalaxyApiClient {
    if (!client) {
        client = createApiClient();
    }

    return client;
}
