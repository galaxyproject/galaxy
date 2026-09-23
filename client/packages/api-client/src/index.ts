/**
 * Galaxy Client API
 * A client library for the Galaxy API
 */

import { createGalaxyApi, type GalaxyApiClient } from "./client";
import { errorMessageAsString } from "./utils/error";

// Re-export all the types from our type compatibility layer
export * from "./api-types";

// SimpleError class for error handling
export class SimpleError extends Error {
    constructor(message: string) {
        super(message);
        this.name = "GalaxyApiError";
    }
}

// Re-export the client functions
export { createGalaxyApi, type GalaxyApiClient };

// For backward compatibility - creates a client with default settings
export function GalaxyApi() {
    return createGalaxyApi();
}

// Utility function to format error messages
export function formatErrorMessage(error: any): string {
    return errorMessageAsString(error);
}
