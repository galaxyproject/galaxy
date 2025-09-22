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
 * @param toolId - The ID of the tool
 * @param toolVersion - The version of the tool
 */
export function useUserToolCredentials(toolId: string, toolVersion: string) {
    const { currentUser } = storeToRefs(useUserStore());

    const sourceCredentialsDefinition = ref<SourceCredentialsDefinition>(
        transformToSourceCredentials(toolId, toolVersion),
    );

    const userToolsServiceCredentialsStore = useUserToolsServiceCredentialsStore();
    const { isBusy, userToolServicesFor } = storeToRefs(userToolsServiceCredentialsStore);

    const currentUserToolServices = computed(() => userToolServicesFor.value(toolId, toolVersion));

    const userServiceFor = computed(() => {
        return (credentialsIdentifier: ServiceCredentialsIdentifier) => {
            return currentUserToolServices.value?.find((service) => {
                return service.name === credentialsIdentifier.name && service.version === credentialsIdentifier.version;
            });
        };
    });
    const userServiceGroupsFor = computed(() => {
        return (credentialsIdentifier: ServiceCredentialsIdentifier) => {
            const foundedService = userServiceFor.value(credentialsIdentifier);
            return foundedService?.groups;
        };
    });

    function getServiceCredentialsDefinitionByKey(key: string): ServiceCredentialsDefinition {
        const definition = sourceCredentialsDefinition.value.services.get(key);
        if (!definition) {
            throw new Error(
                `No definition found for credential service '${key}' in tool ${getToolKey(toolId, toolVersion)}`,
            );
        }
        return definition;
    }

    function getToolServiceCredentialsDefinitionFor(
        serviceIdentifier: ServiceCredentialsIdentifier,
    ): ServiceCredentialsDefinition {
        const key = getKeyFromCredentialsIdentifier(serviceIdentifier);
        return getServiceCredentialsDefinitionByKey(key);
    }

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

    const toolHasRequiredServiceCredentials = computed<boolean>(() => {
        for (const definition of sourceCredentialsDefinition.value.services.values()) {
            if (definition.optional === false) {
                return true;
            }
        }
        return false;
    });

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
     * Get the appropriate banner variant based on credential state
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
     * Check if all credentials (required and optional) are set by the user
     */
    function serviceHasCurrentGroupId(sourceService: UserServiceCredentialsResponse): boolean {
        if (sourceService.groups && sourceService.current_group_id) {
            return true;
        }
        return false;
    }

    /**
     * Fetch or check user credentials for the tool
     */
    async function checkUserCredentials() {
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

    async function createUserCredentials(createSourceCredentialsPayload: CreateSourceCredentialsPayload) {
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
     * Save user credentials for the tool
     */
    async function saveUserCredentials(groupId: string, serviceGroupPayload: ServiceCredentialGroupPayload) {
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
     * Delete a credentials group for a specific service
     */
    async function deleteCredentialsGroup(serviceIdentifier: ServiceCredentialsIdentifier, groupId: string) {
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

    async function selectCurrentCredentialsGroups(serviceCredentials: SelectCurrentGroupPayload[]) {
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
