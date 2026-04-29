import createClient from "openapi-fetch";
import { type GalaxyApiPaths } from "./api-types";

/**
 * Options for creating a Galaxy API client
 */
export interface GalaxyApiOptions {
    /**
     * The base URL of the Galaxy server (e.g., "https://usegalaxy.org")
     * @default window.location.origin
     */
    baseUrl?: string;

    /**
     * API key for authentication
     */
    apiKey?: string;

    /**
     * Custom headers to include with each request
     */
    headers?: Record<string, string>;

    /**
     * Custom fetch options that will be passed to all requests
     */
    fetchOptions?: RequestInit;
}

/**
 * Creates a Galaxy API client with the specified options
 * @param options Configuration options for the Galaxy API client
 * @returns The Galaxy API client
 */
export function createGalaxyApi(options: GalaxyApiOptions | string = {}) {
    // Handle the case where baseUrl is passed as a string for backward compatibility
    const opts = typeof options === "string" ? { baseUrl: options } : options;

    // Default to window.location.origin if no baseUrl is provided
    const baseUrl = opts.baseUrl || window.location.origin;
    const normalizedBaseUrl = baseUrl.endsWith("/") ? baseUrl.slice(0, -1) : baseUrl;

    // Build headers object
    const headers: Record<string, string> = {
        ...(opts.headers || {}),
    };

    // Add API key header if provided
    if (opts.apiKey) {
        headers["x-api-key"] = opts.apiKey;
    }

    // Create the client with all options
    return createClient<GalaxyApiPaths>({
        baseUrl: normalizedBaseUrl,
        headers,
        // Pass any custom fetchOptions directly to createClient
        ...(opts.fetchOptions ? { fetchOptions: opts.fetchOptions } : {}),
    });
}

export type GalaxyApiClient = ReturnType<typeof createGalaxyApi>;
