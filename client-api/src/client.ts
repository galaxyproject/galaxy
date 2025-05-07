import createClient from "openapi-fetch";
import { type GalaxyApiPaths } from "./api-types";

/**
 * Creates a Galaxy API client using the provided base URL
 * @param baseUrl The base URL of the Galaxy server (e.g., "https://usegalaxy.org")
 * @returns The Galaxy API client
 */
export function createGalaxyApi(baseUrl: string = window.location.origin) {
  return createClient<GalaxyApiPaths>({ 
    baseUrl: baseUrl.endsWith('/') ? baseUrl.slice(0, -1) : baseUrl 
  });
}

export type GalaxyApiClient = ReturnType<typeof createGalaxyApi>;