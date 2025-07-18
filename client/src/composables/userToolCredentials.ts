import { computed, ref } from "vue";

import { isRegisteredUser } from "@/api";
import type {
    CreateSourceCredentialsPayload,
    ServiceCredentialsDefinition,
    ServiceCredentialsIdentifier,
    UserCredentials,
} from "@/api/users";
import { useUserCredentialsStore } from "@/stores/userCredentials";
import { useUserStore } from "@/stores/userStore";

import { useToolCredentials } from "./toolCredentials";

/**
 * Vue composable that combines user credentials store with tool credentials management.
 * Provides a unified interface for managing user credentials for a specific tool.
 *
 * @param toolId - The ID of the tool
 * @param toolCredentialsDefinition - Array of service credentials definitions from the tool
 */
export function useUserToolCredentials(toolId: string, toolCredentialsDefinition: ServiceCredentialsDefinition[]) {
    const userStore = useUserStore();
    const userCredentialsStore = useUserCredentialsStore(
        isRegisteredUser(userStore.currentUser) ? userStore.currentUser.id : "anonymous"
    );

    // Use the tool credentials composable for credential definitions
    const {
        sourceCredentialsDefinition,
        hasSomeOptionalCredentials,
        hasSomeRequiredCredentials,
        hasAnyCredentials,
        servicesCount,
    } = useToolCredentials(toolId, toolCredentialsDefinition);

    // State for user's actual credentials
    const userCredentials = ref<UserCredentials[] | undefined>(undefined);
    const isBusy = ref(false);
    const busyMessage = ref<string>("");

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
            if (userStore.isAnonymous) {
                return;
            }

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

    return {
        // From tool credentials
        sourceCredentialsDefinition,
        hasSomeOptionalCredentials,
        hasSomeRequiredCredentials,
        hasAnyCredentials,
        servicesCount,

        // User credentials state
        userCredentials,
        isBusy,
        busyMessage,
        statusVariant,

        // User credentials computed properties
        hasUserProvidedRequiredCredentials,
        hasUserProvidedAllCredentials,
        provideCredentialsButtonTitle,

        // User store properties
        isAnonymous: computed(() => userStore.isAnonymous),

        // Methods
        checkUserCredentials,
        saveUserCredentials,
        deleteCredentialsGroup,
        updateUserCredentials,
    };
}
