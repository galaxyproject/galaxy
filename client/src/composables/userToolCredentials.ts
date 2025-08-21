import { storeToRefs } from "pinia";
import { computed, ref, watch } from "vue";

import type {
    CreateSourceCredentialsPayload,
    ServiceCredentialPayload,
    ServiceCredentialsDefinition,
    ServiceCredentialsIdentifier,
    ServiceGroupPayload,
    UserCredentials,
} from "@/api/users";
import { getKeyFromCredentialsIdentifier } from "@/api/users";
import { useToolCredentials } from "@/composables/toolCredentials";
import { SECRET_PLACEHOLDER, useUserCredentialsStore } from "@/stores/userCredentials";
import { useUserStore } from "@/stores/userStore";

/**
 * Vue composable that combines user credentials store with tool credentials management.
 * Provides a unified interface for managing user credentials for a specific tool.
 *
 * @param toolId - The ID of the tool
 * @param toolVersion - The version of the tool
 */
export function useUserToolCredentials(toolId: string, toolVersion: string) {
    const userStore = useUserStore();
    const userCredentialsStore = useUserCredentialsStore();
    const { userToolCredentials } = storeToRefs(userCredentialsStore);

    const currentUserToolCredentials = computed(() => userToolCredentials.value(toolId, toolVersion));

    const {
        sourceCredentialsDefinition,
        hasSomeOptionalCredentials,
        hasSomeRequiredCredentials,
        hasAnyCredentials,
        servicesCount,
    } = useToolCredentials(toolId, toolVersion);

    const isBusy = ref(false);
    const busyMessage = ref<string>("");
    const mutableUserCredentials = ref<CreateSourceCredentialsPayload>(createUserCredentialsPayload());

    watch(
        () => currentUserToolCredentials.value,
        () => {
            refreshMutableCredentials();
        },
        { deep: true }
    );

    function createUserCredentialsPayload(): CreateSourceCredentialsPayload {
        const serviceCredentials = [];
        for (const key of sourceCredentialsDefinition.value.services.keys()) {
            const userCredentialForService = getUserCredentialsForService(key);

            const currentGroup = userCredentialForService?.current_group_name;
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
        return currentUserToolCredentials.value?.find((c) => getKeyFromCredentialsIdentifier(c) === key);
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
        return getServiceCredentialsDefinitionByKey(key);
    }

    function buildGroupsFromUserCredentials(
        definition: ServiceCredentialsDefinition,
        initialUserCredentials?: UserCredentials
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
        if (!currentUserToolCredentials.value || currentUserToolCredentials.value.length === 0) {
            return false;
        }
        return currentUserToolCredentials.value.every((credentials) => areRequiredSetByUser(credentials));
    });

    /**
     * Check if the user has provided all credentials (required and optional)
     */
    const hasUserProvidedAllCredentials = computed<boolean>(() => {
        if (!currentUserToolCredentials.value || currentUserToolCredentials.value.length === 0) {
            return false;
        }
        return currentUserToolCredentials.value.every(areAllSetByUser);
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
        if (!credentials.groups || !credentials.current_group_name) {
            return false;
        }

        const selectedGroup = credentials.groups[credentials.current_group_name];

        return (
            credentials.credential_definitions.variables.every((v) => {
                const variable = selectedGroup?.variables.find((dv) => v.name === dv.name);
                return v.optional || (variable ? variable.is_set : false);
            }) &&
            credentials.credential_definitions.secrets.every((s) => {
                const secret = selectedGroup?.secrets.find((ds) => s.name === ds.name);
                return s.optional || (secret ? secret.is_set : false);
            })
        );
    }

    /**
     * Check if all credentials (required and optional) are set by the user
     */
    function areAllSetByUser(credentials: UserCredentials): boolean {
        if (!credentials.groups || !credentials.current_group_name) {
            return false;
        }

        const selectedGroup = credentials.groups[credentials.current_group_name];

        return (
            credentials.credential_definitions.variables.every((v) => {
                const variable = selectedGroup?.variables.find((dv) => v.name === dv.name);
                return variable?.is_set ?? false;
            }) &&
            credentials.credential_definitions.secrets.every((s) => {
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
            userCredentialsStore.getAllUserCredentialsForTool(toolId, toolVersion) ??
                (await userCredentialsStore.fetchAllUserCredentialsForTool(toolId, toolVersion));
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
        busyMessage.value = "Saving your credentials";
        isBusy.value = true;
        try {
            await userCredentialsStore.saveUserCredentialsForTool(providedCredentials);
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
        busyMessage.value = "Updating your credentials";
        isBusy.value = true;
        try {
            await userCredentialsStore.deleteCredentialsGroupForTool(toolId, toolVersion, serviceIdentifier, groupName);
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
        currentUserToolCredentials,

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
        refreshMutableCredentials,
        getServiceCredentialsDefinition,
    };
}
