import { storeToRefs } from "pinia";
import { computed, ref } from "vue";

import { isRegisteredUser } from "@/api";
import { getToolKey } from "@/api/tools";
import type {
    CreateSourceCredentialsPayload,
    SelectCurrentGroupPayload,
    ServiceCredentialGroupPayload,
    ServiceCredentialsDefinition,
    ServiceCredentialsIdentifier,
    SourceCredentialsDefinition,
    UserServiceCredentialsResponse,
} from "@/api/userCredentials";
import { getKeyFromCredentialsIdentifier, transformToSourceCredentials } from "@/api/userCredentials";
import { useUserStore } from "@/stores/userStore";
import { SECRET_PLACEHOLDER, useUserToolsServiceCredentialsStore } from "@/stores/userToolsServiceCredentialsStore";

/**
 * Vue composable that combines user credentials store with tool credentials management.
 * Provides a unified interface for managing user credentials for a specific tool.
 *
 * @param {string} toolId - The ID of the tool.
 * @param {string} toolVersion - The version of the tool.
 * @returns {Object} Composable interface with credential management functions and state.
 */
export function useUserToolCredentials(toolId: string, toolVersion: string) {
    const { currentUser } = storeToRefs(useUserStore());

    const userToolsServiceCredentialsStore = useUserToolsServiceCredentialsStore();
    const { isBusy, userToolServicesFor } = storeToRefs(userToolsServiceCredentialsStore);

    /** Source credentials definition transformed for the specific tool. */
    const sourceCredentialsDefinition = ref<SourceCredentialsDefinition>(
        transformToSourceCredentials(toolId, toolVersion),
    );

    /** Current user tool services for the specific tool and version. */
    const currentUserToolServices = computed(() => userToolServicesFor.value(toolId, toolVersion));

    /** Gets user service for a specific credentials identifier. */
    const userServiceFor = computed(() => {
        /**
         * @param {ServiceCredentialsIdentifier} credentialsIdentifier - Service name and version identifier.
         * @returns {UserServiceCredentialsResponse | undefined} User service or undefined if not found.
         */
        return (credentialsIdentifier: ServiceCredentialsIdentifier) => {
            return currentUserToolServices.value?.find((service) => {
                return service.name === credentialsIdentifier.name && service.version === credentialsIdentifier.version;
            });
        };
    });

    /** Gets user service groups for a specific credentials identifier. */
    const userServiceGroupsFor = computed(() => {
        /**
         * @param {ServiceCredentialsIdentifier} credentialsIdentifier - Service name and version identifier.
         * @returns {ServiceCredentialGroupResponse[] | undefined} Service groups or undefined if not found.
         */
        return (credentialsIdentifier: ServiceCredentialsIdentifier) => {
            const foundedService = userServiceFor.value(credentialsIdentifier);
            return foundedService?.groups;
        };
    });

    /**
     * Gets service credentials definition by key.
     * @param {string} key - The service credentials key.
     * @returns {ServiceCredentialsDefinition} Service credentials definition.
     * @throws {Error} If no definition is found for the given key.
     */
    function getServiceCredentialsDefinitionByKey(key: string): ServiceCredentialsDefinition {
        const definition = sourceCredentialsDefinition.value.services.get(key);
        if (!definition) {
            throw new Error(
                `No definition found for credential service '${key}' in tool ${getToolKey(toolId, toolVersion)}`,
            );
        }
        return definition;
    }

    /**
     * Gets tool service credentials definition for a service identifier.
     * @param {ServiceCredentialsIdentifier} serviceIdentifier - Service name and version identifier.
     * @returns {ServiceCredentialsDefinition} Service credentials definition.
     * @throws {Error} If no definition is found for the service identifier.
     */
    function getToolServiceCredentialsDefinitionFor(
        serviceIdentifier: ServiceCredentialsIdentifier,
    ): ServiceCredentialsDefinition {
        const key = getKeyFromCredentialsIdentifier(serviceIdentifier);
        return getServiceCredentialsDefinitionByKey(key);
    }

    /**
     * Builds credential groups from user credentials and service definition.
     * @param {ServiceCredentialsDefinition} definition - Service credentials definition.
     * @param {UserServiceCredentialsResponse} [initialUserCredentials] - Initial user credentials.
     * @returns {ServiceCredentialGroupPayload[]} Array of service credential group payloads.
     */
    function buildGroupsFromUserCredentials(
        definition: ServiceCredentialsDefinition,
        initialUserCredentials?: UserServiceCredentialsResponse,
    ): ServiceCredentialGroupPayload[] {
        const groups: ServiceCredentialGroupPayload[] = [];
        if (initialUserCredentials) {
            const existingGroups = Object.values(initialUserCredentials.groups);
            for (const group of existingGroups) {
                const newGroup: ServiceCredentialGroupPayload = {
                    name: group.name,
                    variables: definition.variables.map((variable) => ({
                        name: variable.name,
                        value: group.variables.find((v) => v.name === variable.name)?.value ?? null,
                    })),
                    secrets: definition.secrets.map((secret) => ({
                        name: secret.name,
                        value: group.secrets.find((s) => s.name === secret.name)?.is_set ? SECRET_PLACEHOLDER : null,
                        alreadySet: group.secrets.find((s) => s.name === secret.name)?.is_set ?? false,
                    })),
                };
                groups.push(newGroup);
            }
        }
        return groups;
    }

    /** Whether user has provided all service credentials (required and optional). */
    const hasUserProvidedAllServiceCredentials = computed<boolean>(() => {
        if (!currentUserToolServices.value || currentUserToolServices.value.length === 0) {
            return false;
        }
        for (const definition of sourceCredentialsDefinition.value.services.values()) {
            const userService = currentUserToolServices.value.find(
                (service) => getKeyFromCredentialsIdentifier(service) === getKeyFromCredentialsIdentifier(definition),
            );
            if (!userService || !serviceHasCurrentGroupId(userService)) {
                return false;
            }
        }
        return true;
    });

    /** Whether tool has any required service credentials. */
    const toolHasRequiredServiceCredentials = computed<boolean>(() => {
        for (const definition of sourceCredentialsDefinition.value.services.values()) {
            if (definition.optional === false) {
                return true;
            }
        }
        return false;
    });

    /** Whether user has provided all required service credentials. */
    const hasUserProvidedAllRequiredServiceCredentials = computed<boolean>(() => {
        if (!currentUserToolServices.value || currentUserToolServices.value.length === 0) {
            return false;
        }

        for (const definition of sourceCredentialsDefinition.value.services.values()) {
            if (definition.optional === false) {
                const userService = currentUserToolServices.value.find(
                    (service) =>
                        getKeyFromCredentialsIdentifier(service) === getKeyFromCredentialsIdentifier(definition),
                );
                if (!userService || !serviceHasCurrentGroupId(userService)) {
                    return false;
                }
            }
        }
        return true;
    });

    /** Whether user has provided some optional service credentials. */
    const hasUserProvidedSomeOptionalServiceCredentials = computed<boolean>(() => {
        if (!currentUserToolServices.value || currentUserToolServices.value.length === 0) {
            return false;
        }

        for (const definition of sourceCredentialsDefinition.value.services.values()) {
            if (definition.optional === true) {
                const userService = currentUserToolServices.value.find(
                    (service) =>
                        getKeyFromCredentialsIdentifier(service) === getKeyFromCredentialsIdentifier(definition),
                );
                if (userService && serviceHasCurrentGroupId(userService)) {
                    return true;
                }
            }
        }
        return false;
    });

    /**
     * Get the appropriate banner variant based on credential state.
     * @returns {string} Banner variant ('info', 'success', or 'warning').
     */
    const statusVariant = computed(() => {
        if (isBusy.value) {
            return "info";
        }
        if (hasUserProvidedAllServiceCredentials.value || hasUserProvidedAllRequiredServiceCredentials.value) {
            return "success";
        }
        return "warning";
    });

    /**
     * Check if all credentials (required and optional) are set by the user.
     * @param {UserServiceCredentialsResponse} sourceService - Source service to check.
     * @returns {boolean} True if service has current group ID.
     */
    function serviceHasCurrentGroupId(sourceService: UserServiceCredentialsResponse): boolean {
        if (sourceService.groups && sourceService.current_group_id) {
            return true;
        }
        return false;
    }

    /**
     * Fetch or check user credentials for the tool.
     * @returns {Promise<void>}
     * @throws {Error} If the credentials check fails.
     */
    async function checkUserCredentials(): Promise<void> {
        if (!isRegisteredUser(currentUser.value)) {
            return;
        }

        try {
            if (!userToolsServiceCredentialsStore.userToolServicesFor(toolId, toolVersion)) {
                await userToolsServiceCredentialsStore.fetchAllUserToolServices(toolId, toolVersion);
            }
        } catch (error) {
            console.error("Error checking user credentials", error);
            throw error;
        }
    }

    /**
     * Creates new user credentials for the tool.
     * @param {CreateSourceCredentialsPayload} createSourceCredentialsPayload - Credential creation payload.
     * @returns {Promise<void>}
     * @throws {Error} If the credential creation fails.
     */
    async function createUserCredentials(
        createSourceCredentialsPayload: CreateSourceCredentialsPayload,
    ): Promise<void> {
        try {
            const serviceIdentifier = createSourceCredentialsPayload.service_credential;
            await userToolsServiceCredentialsStore.createNewCredentialsGroupForTool(
                serviceIdentifier,
                createSourceCredentialsPayload,
            );
        } catch (error) {
            console.error("Error creating user credentials", error);
            throw error;
        }
    }

    /**
     * Save user credentials for the tool.
     * @param {string} groupId - Group ID to update.
     * @param {ServiceCredentialGroupPayload} serviceGroupPayload - Service group payload to save.
     * @returns {Promise<void>}
     * @throws {Error} If the credential save fails.
     */
    async function saveUserCredentials(
        groupId: string,
        serviceGroupPayload: ServiceCredentialGroupPayload,
    ): Promise<void> {
        try {
            await userToolsServiceCredentialsStore.updateUserCredentialsForTool(
                toolId,
                toolVersion,
                groupId,
                serviceGroupPayload,
            );
        } catch (error) {
            console.error("Error updating user credentials", error);
            throw error;
        }
    }

    /**
     * Delete a credentials group for a specific service.
     * @param {ServiceCredentialsIdentifier} serviceIdentifier - Service name and version identifier.
     * @param {string} groupId - Group ID to delete.
     * @returns {Promise<void>}
     * @throws {Error} If the credential deletion fails.
     */
    async function deleteCredentialsGroup(
        serviceIdentifier: ServiceCredentialsIdentifier,
        groupId: string,
    ): Promise<void> {
        try {
            await userToolsServiceCredentialsStore.deleteCredentialsGroupForTool(
                toolId,
                toolVersion,
                serviceIdentifier,
                groupId,
            );
        } catch (error) {
            console.error("Error deleting user credentials group", error);
            throw error;
        }
    }

    /**
     * Selects current credentials groups for the tool.
     * @param {SelectCurrentGroupPayload[]} serviceCredentials - Array of service credentials to select.
     * @returns {Promise<void>}
     * @throws {Error} If the selection fails.
     */
    async function selectCurrentCredentialsGroups(serviceCredentials: SelectCurrentGroupPayload[]): Promise<void> {
        try {
            await userToolsServiceCredentialsStore.selectCurrentCredentialsGroupsForTool(
                toolId,
                toolVersion,
                serviceCredentials,
            );
        } catch (error) {
            console.error("Error selecting current credentials groups", error);
            throw error;
        }
    }

    return {
        sourceCredentialsDefinition,
        currentUserToolServices,
        userServiceFor,
        userServiceGroupsFor,
        statusVariant,
        toolHasRequiredServiceCredentials,
        hasUserProvidedAllServiceCredentials,
        hasUserProvidedAllRequiredServiceCredentials,
        hasUserProvidedSomeOptionalServiceCredentials,
        checkUserCredentials,
        createUserCredentials,
        saveUserCredentials,
        deleteCredentialsGroup,
        buildGroupsFromUserCredentials,
        getToolServiceCredentialsDefinitionFor,
        selectCurrentCredentialsGroups,
    };
}
