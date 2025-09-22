import type { components } from "@/api";
import { useToolsServiceCredentialsDefinitionsStore } from "@/stores/toolsServiceCredentialsDefinitionsStore";

/**
 * Just an alias for a string that represents a unique key for a service credentials identifier.
 * The key is a combination of the service name and version, formatted as "name-version".
 */
type ServiceCredentialsIdentifierKey = string;

export type CredentialType = "variable" | "secret";
export type ServiceCredentialsGroup = components["schemas"]["CredentialGroupResponse"];
export type CreateSourceCredentialsPayload = components["schemas"]["CreateSourceCredentialsPayload"];
export type UserCredentialsResponse = components["schemas"]["UserCredentialsResponse"];
export type ServiceCredentialPayload = components["schemas"]["ServiceCredentialPayload"];
export type ServiceGroupPayload = components["schemas"]["ServiceGroupPayload"];
export type UserToolsServiceCredentialsFull = components["schemas"]["ExtendedUserCredentialsResponse"];
export type SelectCurrentGroupPayload = components["schemas"]["SelectCurrentGroupPayload"];
export type ServiceParameterDefinition = components["schemas"]["CredentialDefinitionResponse"];
export type ServiceCredentialsDefinition = components["schemas"]["ServiceCredentialsDefinition"];

export interface ServiceCredentialsIdentifier {
    name: string;
    version: string;
}

/**
 * Represents the definition of credentials for a particular source.
 * A source can be an entity using a service that uses credentials, for example, a tool.
 * A source may accept multiple services, each with its own credentials.
 *
 * The `services` map is indexed by the service name and version using the `getKeyFromCredentialsIdentifier` function.
 */
export interface SourceCredentialsDefinition {
    sourceType: string;
    sourceId: string;
    services: Map<ServiceCredentialsIdentifierKey, ServiceCredentialsDefinition>;
}

// TODO: temporal definition, should be imported from the corresponding ServiceCredentialsContext API schema model
export interface ServiceCredentialsContext {
    user_credentials_id: string | null;
    name: string;
    version: string;
    selected_group: {
        id: string | null;
        name: string;
    };
}

export function getKeyFromCredentialsIdentifier(
    credentialsIdentifier: ServiceCredentialsIdentifier,
): ServiceCredentialsIdentifierKey {
    return `${credentialsIdentifier.name}-${credentialsIdentifier.version}`;
}

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
