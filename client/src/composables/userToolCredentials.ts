import { storeToRefs } from "pinia";
import { computed, ref } from "vue";

import type {
    CreateSourceCredentialsPayload,
    ServiceCredentialsDefinition,
    ServiceCredentialsIdentifier,
    ServiceGroupPayload,
    UserSourceService,
} from "@/api/users";
import { getKeyFromCredentialsIdentifier } from "@/api/users";
import { useToolCredentials } from "@/composables/toolCredentials";
import { useUserStore } from "@/stores/userStore";
import { SECRET_PLACEHOLDER, useUserToolsServicesStore } from "@/stores/userToolsServicesStore";

/**
 * Vue composable that combines user credentials store with tool credentials management.
 * Provides a unified interface for managing user credentials for a specific tool.
 *
 * @param toolId - The ID of the tool
 * @param toolVersion - The version of the tool
 */
export function useUserToolCredentials(toolId: string, toolVersion: string) {
    const userStore = useUserStore();
    const userToolsServicesStore = useUserToolsServicesStore();
    const { userToolServicesFor, userToolServiceGroups } = storeToRefs(userToolsServicesStore);
    const {
        sourceCredentialsDefinition,
        hasSomeOptionalCredentials,
        hasSomeRequiredCredentials,
        hasAnyCredentials,
        servicesCount,
    } = useToolCredentials(toolId, toolVersion);

    const currentUserToolServices = computed(() => userToolServicesFor.value(toolId, toolVersion));
    const userServiceGroupsFor = computed(() => {
        return (credentialsIdentifier: ServiceCredentialsIdentifier) => {
            const foundedService = currentUserToolServices.value?.find((service) => {
                return service.name === credentialsIdentifier.name && service.version === credentialsIdentifier.version;
            });

            return foundedService?.groups;
        };
    });

    const isBusy = ref(false);
    const busyMessage = ref<string>("");

    function getServiceCredentialsDefinitionByKey(key: string): ServiceCredentialsDefinition {
        const definition = sourceCredentialsDefinition.value.services.get(key);
        if (!definition) {
            throw new Error(`No definition found for credential service '${key}' in tool ${toolId}`);
        }
        return definition;
    }

    function getServiceCredentialsDefinition(
        serviceIdentifier: ServiceCredentialsIdentifier
    ): ServiceCredentialsDefinition {
        const key = getKeyFromCredentialsIdentifier(serviceIdentifier);
        return getServiceCredentialsDefinitionByKey(key);
    }

    function buildGroupsFromUserCredentials(
        definition: ServiceCredentialsDefinition,
        initialUserCredentials?: UserSourceService
    ): ServiceGroupPayload[] {
        const groups: ServiceGroupPayload[] = [];
        if (initialUserCredentials) {
            const existingGroups = Object.values(initialUserCredentials.groups);
            for (const group of existingGroups) {
                const newGroup: ServiceGroupPayload = {
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

    /**
     * Check if the user has provided all required credentials
     */
    const hasUserProvidedRequiredCredentials = computed<boolean>(() => {
        if (!currentUserToolServices.value || currentUserToolServices.value.length === 0) {
            return false;
        }
        return currentUserToolServices.value.every((credentials) => areRequiredSetByUser(credentials));
    });

    /**
     * Check if the user has provided all credentials (required and optional)
     */
    const hasUserProvidedAllCredentials = computed<boolean>(() => {
        if (!currentUserToolServices.value || currentUserToolServices.value.length === 0) {
            return false;
        }
        return currentUserToolServices.value.every(areAllSetByUser);
    });

    /**
     * Get the appropriate button title for managing credentials
     */
    const provideCredentialsButtonTitle = computed(() => {
        return hasUserProvidedRequiredCredentials.value ? "Manage credentials" : "Provide credentials";
    });

    /**
     * Get the appropriate banner variant based on credential state
     */
    const statusVariant = computed(() => {
        if (isBusy.value) {
            return "info";
        }
        return hasUserProvidedRequiredCredentials.value ? "success" : "warning";
    });

    /**
     * Check if all required credentials are set by the user
     */
    function areRequiredSetByUser(sourceService: UserSourceService): boolean {
        if (!sourceService.groups || !sourceService.current_group_id) {
            return false;
        }

        const serviceDefinitions = getServiceCredentialsDefinition(sourceService);
        const selectedGroup = userToolServiceGroups.value[sourceService.current_group_id];

        return (
            serviceDefinitions.variables.every((v) => {
                const variable = selectedGroup?.variables.find((dv) => v.name === dv.name);
                return v.optional || (variable?.value ?? false);
            }) &&
            serviceDefinitions.secrets.every((s) => {
                const secret = selectedGroup?.secrets.find((ds) => s.name === ds.name);
                return s.optional || (secret?.is_set ?? false);
            })
        );
    }

    /**
     * Check if all credentials (required and optional) are set by the user
     */
    function areAllSetByUser(sourceService: UserSourceService): boolean {
        if (!sourceService.groups || !sourceService.current_group_id) {
            return false;
        }

        const serviceDefinitions = getServiceCredentialsDefinition(sourceService);
        const selectedGroup = userToolServiceGroups.value[sourceService.current_group_id];

        return (
            serviceDefinitions.variables.every((v) => {
                const variable = selectedGroup?.variables.find((dv) => v.name === dv.name);
                return variable?.value ?? false;
            }) &&
            serviceDefinitions.secrets.every((s) => {
                const secret = selectedGroup?.secrets.find((ds) => s.name === ds.name);
                return secret?.is_set ?? false;
            })
        );
    }

    /**
     * Fetch or check user credentials for the tool
     */
    async function checkUserCredentials() {
        if (userStore.isAnonymous) {
            return;
        }

        busyMessage.value = "Checking your credentials";
        isBusy.value = true;
        try {
            if (!userToolsServicesStore.userServicesExistForTool(toolId, toolVersion)) {
                await userToolsServicesStore.fetchAllUserToolServices(toolId, toolVersion);
            }
        } catch (error) {
            console.error("Error checking user credentials", error);
            throw error;
        } finally {
            isBusy.value = false;
            busyMessage.value = "";
        }
    }

    async function createUserCredentials(createSourceCredentialsPayload: CreateSourceCredentialsPayload) {
        busyMessage.value = "Creating your credentials";
        isBusy.value = true;
        try {
            await userToolsServicesStore.createNewCredentialsGroupForTool(createSourceCredentialsPayload);
        } catch (error) {
            console.error("Error creating user credentials", error);
            throw error;
        } finally {
            isBusy.value = false;
            busyMessage.value = "";
        }
    }

    /**
     * Save user credentials for the tool
     */
    async function saveUserCredentials(groupId: string, serviceGroupPayload: ServiceGroupPayload) {
        busyMessage.value = "Updating your credentials";
        isBusy.value = true;
        try {
            await userToolsServicesStore.updateUserCredentialsForTool(
                toolId,
                toolVersion,
                groupId,
                serviceGroupPayload
            );
        } catch (error) {
            console.error("Error updating user credentials", error);
            throw error;
        } finally {
            isBusy.value = false;
            busyMessage.value = "";
        }
    }

    /**
     * Delete a credentials group for a specific service
     */
    async function deleteCredentialsGroup(serviceIdentifier: ServiceCredentialsIdentifier, groupId: string) {
        busyMessage.value = "Updating your credentials";
        isBusy.value = true;
        try {
            console.log("286 Deleting group:", groupId);
            await userToolsServicesStore.deleteCredentialsGroupForTool(toolId, toolVersion, serviceIdentifier, groupId);
            await userToolsServicesStore.fetchAllUserToolServices(toolId, toolVersion);
        } catch (error) {
            console.error("Error deleting user credentials group", error);
            throw error;
        } finally {
            isBusy.value = false;
            busyMessage.value = "";
        }
    }

    return {
        sourceCredentialsDefinition,
        hasSomeOptionalCredentials,
        hasSomeRequiredCredentials,
        hasAnyCredentials,
        servicesCount,

        /** The credentials for the user already stored in the system */
        currentUserToolServices,
        userServiceGroupsFor,

        /** Busy state for operations */
        isBusy,

        /** Message to display during busy operations */
        busyMessage,

        /** Color variant for status messages according to current state */
        statusVariant,

        // User credentials computed properties
        hasUserProvidedRequiredCredentials,
        hasUserProvidedAllCredentials,
        provideCredentialsButtonTitle,

        // Methods
        checkUserCredentials,
        createUserCredentials,
        saveUserCredentials,
        deleteCredentialsGroup,
        buildGroupsFromUserCredentials,
        getServiceCredentialsDefinition,
    };
}
