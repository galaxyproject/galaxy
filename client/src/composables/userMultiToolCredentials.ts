import { storeToRefs } from "pinia";
import { computed, reactive } from "vue";

import type { ToolIdentifier } from "@/api/tools";
import { getToolKey } from "@/api/tools";
import type {
    SelectCurrentGroupPayload,
    ServiceCredentialsIdentifier,
    SourceCredentialsDefinition,
    UserServiceCredentialsResponse,
} from "@/api/userCredentials";
import { useUserToolCredentials } from "@/composables/userToolCredentials";
import { useUserToolsServiceCredentialsStore } from "@/stores/userToolsServiceCredentialsStore";

/**
 * Vue composable for managing user credentials across multiple tools.
 * Provides a unified interface for handling credentials for multiple tools simultaneously.
 *
 * @param {ToolIdentifier[]} tools - Array of tool identifiers with toolId and toolVersion.
 * @returns {Object} Composable interface with multi-tool credential management functions and state.
 */
export function useUserMultiToolCredentials(tools: ToolIdentifier[]) {
    const { isBusy } = storeToRefs(useUserToolsServiceCredentialsStore());

    /** Map of tool credentials by tool key. */
    const userToolCredentialsByKey = reactive(new Map<string, ReturnType<typeof useUserToolCredentials>>());

    /** Initialize user tool credentials for each tool. */
    tools.forEach(({ toolId, toolVersion }) => {
        const toolKey = getToolKey(toolId, toolVersion);
        if (!userToolCredentialsByKey.has(toolKey)) {
            userToolCredentialsByKey.set(toolKey, useUserToolCredentials(toolId, toolVersion));
        }
    });

    /** Gets source credentials definition for a specific tool. */
    const sourceCredentialsDefinitionFor = computed(() => {
        /**
         * Gets source credentials definition for a specific tool.
         * @param {string} toolId - Tool identifier.
         * @param {string} toolVersion - Tool version.
         * @returns {SourceCredentialsDefinition} Source credentials definition for the tool.
         * @throws {Error} If no credentials are found for the tool.
         */
        return (toolId: string, toolVersion: string): SourceCredentialsDefinition => {
            const toolKey = getToolKey(toolId, toolVersion);
            const userToolCredentials = userToolCredentialsByKey.get(toolKey);
            if (!userToolCredentials) {
                throw new Error(
                    `No credentials found for tool ${getToolKey(
                        toolId,
                        toolVersion,
                    )}. Make sure it's included in the tools array.`,
                );
            }
            return userToolCredentials.sourceCredentialsDefinition.value;
        };
    });

    /** Gets user service for a specific tool and service identifier. */
    const userServiceForTool = computed(() => {
        /**
         * Gets user service for a specific tool and service identifier.
         * @param {string} toolId - Tool identifier.
         * @param {string} toolVersion - Tool version.
         * @param {ServiceCredentialsIdentifier} sd - Service credentials identifier.
         * @returns {UserServiceCredentialsResponse | undefined} User service or undefined if not found.
         */
        return (
            toolId: string,
            toolVersion: string,
            sd: ServiceCredentialsIdentifier,
        ): UserServiceCredentialsResponse | undefined => {
            const toolKey = getToolKey(toolId, toolVersion);
            const userToolCredentials = userToolCredentialsByKey.get(toolKey);
            return userToolCredentials?.userServiceFor.value(sd);
        };
    });

    /** Whether some tools have required service credentials. */
    const someToolsHasRequiredServiceCredentials = computed(() => {
        return Array.from(userToolCredentialsByKey.values()).some(
            (userToolCredentials) => userToolCredentials.toolHasRequiredServiceCredentials.value,
        );
    });

    /** Whether user has provided all service credentials for all tools. */
    const hasUserProvidedAllToolsServiceCredentials = computed(() => {
        return Array.from(userToolCredentialsByKey.values()).every(
            (userToolCredentials) => userToolCredentials.hasUserProvidedAllServiceCredentials.value,
        );
    });

    /** Whether user has provided all required service credentials for all tools. */
    const hasUserProvidedAllRequiredToolsServiceCredentials = computed(() => {
        return Array.from(userToolCredentialsByKey.values()).every(
            (userToolCredentials) => userToolCredentials.hasUserProvidedAllRequiredServiceCredentials.value,
        );
    });

    /** Whether user has provided some optional service credentials for any tools. */
    const hasUserProvidedSomeOptionalToolsServiceCredentials = computed(() => {
        return Array.from(userToolCredentialsByKey.values()).some(
            (userToolCredentials) => userToolCredentials.hasUserProvidedSomeOptionalServiceCredentials.value,
        );
    });

    /**
     * Get the appropriate status variant based on overall credential state.
     * "info" - when busy checking credentials.
     * "success" - when all required credentials are provided or no required credentials exist.
     * "warning" - when some required credentials are missing.
     * @returns {"info" | "success" | "warning"} Status variant.
     */
    const statusVariant = computed<"info" | "success" | "warning">(() => {
        if (isBusy.value) {
            return "info";
        }
        if (
            hasUserProvidedAllToolsServiceCredentials.value ||
            hasUserProvidedAllRequiredToolsServiceCredentials.value
        ) {
            return "success";
        }
        if (someToolsHasRequiredServiceCredentials.value) {
            return "warning";
        }
        if (!someToolsHasRequiredServiceCredentials.value) {
            return "success";
        }
        return "info";
    });

    /**
     * Checks user credentials for all tools.
     * @returns {Promise<void[]>} Promise that resolves when all credential checks complete.
     * @throws {Error} If any credential check fails.
     */
    async function checkAllUserCredentials(): Promise<void[]> {
        const promises = Array.from(userToolCredentialsByKey.values()).map((c) => c.checkUserCredentials());
        return await Promise.all(promises);
    }

    /**
     * Gets tool credentials for a specific tool.
     * @param {string} toolId - Tool identifier.
     * @param {string} toolVersion - Tool version.
     * @returns {ReturnType<typeof useUserToolCredentials>} Tool credentials interface.
     * @throws {Error} If no credentials are found for the tool.
     */
    function getToolCredentials(toolId: string, toolVersion: string): ReturnType<typeof useUserToolCredentials> {
        const toolKey = getToolKey(toolId, toolVersion);
        const userToolCredentials = userToolCredentialsByKey.get(toolKey);
        if (!userToolCredentials) {
            throw new Error(
                `No credentials found for tool ${getToolKey(
                    toolId,
                    toolVersion,
                )}. Make sure it's included in the tools array.`,
            );
        }
        return userToolCredentials;
    }

    /**
     * Selects current credentials groups for a specific tool.
     * @param {string} toolId - Tool identifier.
     * @param {string} toolVersion - Tool version.
     * @param {SelectCurrentGroupPayload[]} serviceCredentials - Array of service credentials to select.
     * @returns {Promise<void>} Promise that resolves when selection is complete.
     * @throws {Error} If the tool is not found or selection fails.
     */
    function selectCurrentCredentialsGroupsForTool(
        toolId: string,
        toolVersion: string,
        serviceCredentials: SelectCurrentGroupPayload[],
    ): Promise<void> {
        const toolCredentials = getToolCredentials(toolId, toolVersion);
        return toolCredentials.selectCurrentCredentialsGroups(serviceCredentials);
    }

    return {
        userServiceForTool,
        sourceCredentialsDefinitionFor,
        statusVariant,
        someToolsHasRequiredServiceCredentials,
        hasUserProvidedAllToolsServiceCredentials,
        hasUserProvidedAllRequiredToolsServiceCredentials,
        hasUserProvidedSomeOptionalToolsServiceCredentials,
        checkAllUserCredentials,
        selectCurrentCredentialsGroupsForTool,
    };
}
