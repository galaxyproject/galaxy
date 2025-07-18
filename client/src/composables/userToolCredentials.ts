import { computed, ref, watch } from "vue";

import {
    type CreateSourceCredentialsPayload,
    getKeyFromCredentialsIdentifier,
    type ServiceCredentialPayload,
    type ServiceCredentialsDefinition,
    type ServiceCredentialsIdentifier,
    type ServiceGroupPayload,
    type UserCredentials,
} from "@/api/users";
import { SECRET_PLACEHOLDER, useUserCredentialsStore } from "@/stores/userCredentials";

import { useToolCredentials } from "./toolCredentials";

/**
 * Vue composable that combines user credentials store with tool credentials management.
 * Provides a unified interface for managing user credentials for a specific tool.
 *
 * @param toolId - The ID of the tool
 * @param toolVersion - The version of the tool
 * @param toolCredentialsDefinition - Array of service credentials definitions from the tool
 */
export function useUserToolCredentials(
    toolId: string,
    toolVersion: string,
    toolCredentialsDefinition: ServiceCredentialsDefinition[]
) {
    const userCredentialsStore = useUserCredentialsStore();

    // Use the tool credentials composable for credential definitions
    const {
        sourceCredentialsDefinition,
        hasSomeOptionalCredentials,
        hasSomeRequiredCredentials,
        hasAnyCredentials,
        servicesCount,
    } = useToolCredentials(toolId, toolCredentialsDefinition);

    const userCredentials = ref<UserCredentials[] | undefined>(undefined);
    const isBusy = ref(false);
    const busyMessage = ref<string>("");
    const mutableUserCredentials = ref<CreateSourceCredentialsPayload>(createUserCredentialsPayload());

    watch(
        userCredentials,
        () => {
            console.debug("User credentials changed, updating mutable credentials");
            refreshMutableCredentials();
        },
        { deep: true }
    );

    function createUserCredentialsPayload(): CreateSourceCredentialsPayload {
        const serviceCredentials = [];
        for (const key of sourceCredentialsDefinition.value.services.keys()) {
            const userCredentialForService = getUserCredentialsForService(key);

            const currentGroup = userCredentialForService?.current_group_name ?? "default";
            const definition = getServiceCredentialsDefinitionByKey(key);
            const groups = buildGroupsFromUserCredentials(definition, userCredentialForService);
            const credential: ServiceCredentialPayload = {
                name: definition.name,
                version: definition.version,
                current_group: currentGroup,
                groups,
            };
            serviceCredentials.push(credential);
        }

        const providedCredentials: CreateSourceCredentialsPayload = {
            source_type: "tool",
            source_id: toolId,
            source_version: toolVersion,
            credentials: serviceCredentials,
        };
        return providedCredentials;
    }

    function getUserCredentialsForService(key: string): UserCredentials | undefined {
        return userCredentials.value?.find((c) => getKeyFromCredentialsIdentifier(c) === key);
    }

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
        const definition = sourceCredentialsDefinition.value.services.get(key);
        if (!definition) {
            throw new Error(`No ServiceCredentialsDefinition found for service '${key}'`);
        }
        return definition;
    }

    function buildGroupsFromUserCredentials(
        definition: ServiceCredentialsDefinition,
        userCredentials?: UserCredentials
    ): ServiceGroupPayload[] {
        const groups: ServiceGroupPayload[] = [];
        if (userCredentials) {
            const existingGroups = Object.values(userCredentials.groups);
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
        } else {
            const defaultGroup: ServiceGroupPayload = {
                name: "default",
                variables: definition.variables.map((variable) => ({
                    name: variable.name,
                    value: null,
                })),
                secrets: definition.secrets.map((secret) => ({
                    name: secret.name,
                    value: null,
                })),
            };
            groups.push(defaultGroup);
        }
        return groups;
    }

    /**
     * Check if the user has provided all required credentials
     */
    const hasUserProvidedRequiredCredentials = computed<boolean>(() => {
        if (!userCredentials.value || userCredentials.value.length === 0) {
            return false;
        }
        return userCredentials.value.every((credentials) => areRequiredSetByUser(credentials));
    });

    /**
     * Check if the user has provided all credentials (required and optional)
     */
    const hasUserProvidedAllCredentials = computed<boolean>(() => {
        if (!userCredentials.value || userCredentials.value.length === 0) {
            return false;
        }
        return userCredentials.value.every(areAllSetByUser);
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
    function areRequiredSetByUser(credentials: UserCredentials): boolean {
        const selectedGroup = credentials.groups[credentials.current_group_name];
        if (!selectedGroup) {
            return false;
        }
        return (
            credentials.credential_definitions.variables.every((v) => {
                const variable = selectedGroup.variables.find((dv) => v.name === dv.name);
                return v.optional || (variable ? variable.is_set : false);
            }) &&
            credentials.credential_definitions.secrets.every((s) => {
                const secret = selectedGroup.secrets.find((ds) => s.name === ds.name);
                return s.optional || (secret ? secret.is_set : false);
            })
        );
    }

    /**
     * Check if all credentials (required and optional) are set by the user
     */
    function areAllSetByUser(credentials: UserCredentials): boolean {
        const selectedGroup = credentials.groups[credentials.current_group_name];
        if (!selectedGroup) {
            return false;
        }
        return (
            credentials.credential_definitions.variables.every((v) => {
                const variable = selectedGroup.variables.find((dv) => v.name === dv.name);
                return variable?.is_set ?? false;
            }) &&
            credentials.credential_definitions.secrets.every((s) => {
                const secret = selectedGroup.secrets.find((ds) => s.name === ds.name);
                return secret?.is_set ?? false;
            })
        );
    }

    /**
     * Fetch or check user credentials for the tool
     */
    async function checkUserCredentials() {
        busyMessage.value = "Checking your credentials...";
        isBusy.value = true;
        try {
            userCredentials.value =
                userCredentialsStore.getAllUserCredentialsForTool(toolId) ??
                (await userCredentialsStore.fetchAllUserCredentialsForTool(toolId));
        } catch (error) {
            console.error("Error checking user credentials", error);
            throw error;
        } finally {
            isBusy.value = false;
        }
    }

    /**
     * Save user credentials for the tool
     */
    async function saveUserCredentials(providedCredentials: CreateSourceCredentialsPayload) {
        busyMessage.value = "Saving your credentials...";
        isBusy.value = true;
        try {
            userCredentials.value = await userCredentialsStore.saveUserCredentialsForTool(providedCredentials);
            return userCredentials.value;
        } catch (error) {
            console.error("Error saving user credentials", error);
            throw error;
        } finally {
            isBusy.value = false;
        }
    }

    /**
     * Delete a credentials group for a specific service
     */
    async function deleteCredentialsGroup(serviceIdentifier: ServiceCredentialsIdentifier, groupName: string) {
        busyMessage.value = "Updating your credentials...";
        isBusy.value = true;
        try {
            await userCredentialsStore.deleteCredentialsGroupForTool(toolId, serviceIdentifier, groupName);
            // Refresh credentials after deletion
            await checkUserCredentials();
        } catch (error) {
            console.error("Error deleting user credentials group", error);
            throw error;
        } finally {
            isBusy.value = false;
        }
    }

    /**
     * Update user credentials reference
     */
    function updateUserCredentials(data?: UserCredentials[]) {
        userCredentials.value = data;
    }

    /**
     * Refresh the mutable credentials payload based on current user credentials
     */
    function refreshMutableCredentials() {
        mutableUserCredentials.value = createUserCredentialsPayload();
    }

    return {
        sourceCredentialsDefinition,
        hasSomeOptionalCredentials,
        hasSomeRequiredCredentials,
        hasAnyCredentials,
        servicesCount,

        /** The credentials for the user already stored in the system */
        userCredentials,

        /** Mutable credentials for editing */
        mutableUserCredentials,

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
        saveUserCredentials,
        deleteCredentialsGroup,
        updateUserCredentials,
        refreshMutableCredentials,
        getServiceCredentialsDefinition,
    };
}
