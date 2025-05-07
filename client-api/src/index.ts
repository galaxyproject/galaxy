/**
 * Galaxy Client API
 * A client library for the Galaxy API
 */

import { createGalaxyApi, type GalaxyApiClient } from "./client";
import { SimpleError } from "./utils/simple-error";

// Re-export all the types from our type compatibility layer
export * from "./api-types";

// Re-export the client functions
export { 
  createGalaxyApi, 
  type GalaxyApiClient,
  SimpleError 
};

// For backward compatibility - creates a client with default settings
export function GalaxyApi() {
  return createGalaxyApi();
}