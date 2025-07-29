import { computed, readonly, ref } from "vue";

import {
    type ServiceCredentialsDefinition,
    type SourceCredentialsDefinition,
    transformToSourceCredentials,
} from "@/api/users";

/**
 * Vue composable for managing tool credentials and source credentials definitions.
 *
 * This composable provides functionality to:
 * - Convert tool credentials definitions to source credentials definitions
 * - Check if credentials have optional or required fields
 * - Provide useful computed properties for UI components
 *
 * @param toolId - The ID of the tool
 * @param toolCredentialsDefinition - Array of service credentials definitions from the tool
 */
export function useToolCredentials(toolId: string, toolCredentialsDefinition: ServiceCredentialsDefinition[]) {
    const sourceCredentialsDefinition = ref<SourceCredentialsDefinition>(
        transformToSourceCredentials(toolId, toolCredentialsDefinition)
    );

    /**
     * Check if any service has optional credentials (secrets or variables)
     */
    const hasSomeOptionalCredentials = computed<boolean>(() => {
        for (const service of sourceCredentialsDefinition.value.services.values()) {
            if (
                service.secrets.some((secret) => secret.optional) ||
                service.variables.some((variable) => variable.optional)
            ) {
                return true;
            }
        }
        return false;
    });

    /**
     * Check if any service has required credentials (secrets or variables)
     */
    const hasSomeRequiredCredentials = computed<boolean>(() => {
        for (const service of sourceCredentialsDefinition.value.services.values()) {
            if (
                service.secrets.some((secret) => !secret.optional) ||
                service.variables.some((variable) => !variable.optional)
            ) {
                return true;
            }
        }
        return false;
    });

    /**
     * Check if the tool has any credentials at all
     */
    const hasAnyCredentials = computed<boolean>(() => {
        for (const service of sourceCredentialsDefinition.value.services.values()) {
            if (service.secrets.length > 0 || service.variables.length > 0) {
                return true;
            }
        }
        return false;
    });

    /**
     * Get the total number of services
     */
    const servicesCount = computed(() => sourceCredentialsDefinition.value.services.size);

    return {
        sourceCredentialsDefinition: readonly(sourceCredentialsDefinition),
        hasSomeOptionalCredentials,
        hasSomeRequiredCredentials,
        hasAnyCredentials,
        servicesCount,
    };
}
