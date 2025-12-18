/**
 * User Credentials API
 *
 * This module provides type definitions, interfaces, and utility functions
 * for managing user service credentials. It includes types for credential
 * groups, service definitions, and helper functions for credential management.
 *
 * @module userCredentials
 */

import type { components } from "@/api";
import { useToolsServiceCredentialsDefinitionsStore } from "@/stores/toolsServiceCredentialsDefinitionsStore";

/**
 * Just an alias for a string that represents a unique key for a service credentials identifier.
 * The key is a combination of the service name and version, formatted as "name-version".
 */
type ServiceCredentialsIdentifierKey = string;

/** Type for credential field types. */
export type CredentialType = "variable" | "secret";
/** Service credential group response from API. */
export type ServiceCredentialGroupResponse = components["schemas"]["ServiceCredentialGroupResponse"];
/** Payload for creating source credentials. */
export type CreateSourceCredentialsPayload = components["schemas"]["CreateSourceCredentialsPayload"];
/** User service credentials response from API. */
export type UserServiceCredentialsResponse = components["schemas"]["UserServiceCredentialsResponse"];
/** Service credential payload for API requests. */
export type ServiceCredentialPayload = components["schemas"]["ServiceCredentialPayload"];
/** Service credential group payload for API requests. */
export type ServiceCredentialGroupPayload = components["schemas"]["ServiceCredentialGroupPayload"];
/** User service credentials with definition response from API. */
export type UserServiceCredentialsWithDefinitionResponse =
    components["schemas"]["UserServiceCredentialsWithDefinitionResponse"];
/** Payload for selecting current credential group. */
export type SelectCurrentGroupPayload = components["schemas"]["SelectCurrentGroupPayload"];
/** Service parameter definition from API. */
export type ServiceParameterDefinition = components["schemas"]["ServiceParameterDefinition"];
/** Service credentials definition from API. */
export type ServiceCredentialsDefinition = components["schemas"]["ServiceCredentialsDefinition"];

/**
 * Service credentials identifier interface.
 * @interface ServiceCredentialsIdentifier
 */
export interface ServiceCredentialsIdentifier {
    /** Service name. */
    name: string;
    /** Service version. */
    version: string;
}

/**
 * Represents the definition of credentials for a particular source.
 * A source can be an entity using a service that uses credentials, for example, a tool.
 * A source may accept multiple services, each with its own credentials.
 *
 * The `services` map is indexed by the service name and version using the `getKeyFromCredentialsIdentifier` function.
 * @interface SourceCredentialsDefinition
 */
export interface SourceCredentialsDefinition {
    /** Type of the source (e.g., "tool"). */
    sourceType: string;
    /** Unique identifier for the source. */
    sourceId: string;
    /** Map of services indexed by service identifier key. */
    services: Map<ServiceCredentialsIdentifierKey, ServiceCredentialsDefinition>;
}

/**
 * Service credentials context interface.
 * @interface ServiceCredentialsContext
 * @todo Replace with proper API schema model when available.
 */
export interface ServiceCredentialsContext {
    /** User credentials ID or null if not set. */
    user_credentials_id: string | null;
    /** Service name. */
    name: string;
    /** Service version. */
    version: string;
    /** Selected credential group information. */
    selected_group: {
        /** Group ID or null if not selected. */
        id: string | null;
        /** Group name. */
        name: string;
    };
}

/**
 * Generates a unique key from service credentials identifier
 * @param {ServiceCredentialsIdentifier} credentialsIdentifier - Service credentials identifier
 * @returns {ServiceCredentialsIdentifierKey} Unique key in format "name-version"
 */
export function getKeyFromCredentialsIdentifier(
    credentialsIdentifier: ServiceCredentialsIdentifier,
): ServiceCredentialsIdentifierKey {
    return `${credentialsIdentifier.name}-${credentialsIdentifier.version}`;
}

/**
 * Transforms tool information into source credentials definition
 * @param {string} toolId - The id of the tool
 * @param {string} toolVersion - The version of the tool
 * @returns {SourceCredentialsDefinition} Source credentials definition for the tool
 */
export function transformToSourceCredentials(toolId: string, toolVersion: string): SourceCredentialsDefinition {
    const { getToolServiceCredentialsDefinitionsFor } = useToolsServiceCredentialsDefinitionsStore();

    const toolCredentialsDefinitions = getToolServiceCredentialsDefinitionsFor(toolId, toolVersion);

    const services = new Map(
        toolCredentialsDefinitions.map((service) => [getKeyFromCredentialsIdentifier(service), service]),
    );

    return {
        sourceType: "tool",
        sourceId: toolId,
        services,
    };
}
