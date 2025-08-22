import { computed, reactive } from "vue";

import type { CreateSourceCredentialsPayload, ServiceCredentialsIdentifier, UserCredentials } from "@/api/users";
import { useUserToolCredentials } from "@/composables/userToolCredentials";

export interface ToolIdentifier {
    toolId: string;
    toolVersion: string;
}

export function useUserMultiToolCredentials(tools: ToolIdentifier[]) {
    // Create a map to store individual tool credential composables
    const toolCredentialsMap = reactive(new Map<string, ReturnType<typeof useUserToolCredentials>>());

    // Helper function to create a unique key for a tool
    const getToolKey = (toolId: string, toolVersion: string) => `${toolId}@${toolVersion}`;

    // Initialize tool credentials for each tool
    tools.forEach(({ toolId, toolVersion }) => {
        const key = getToolKey(toolId, toolVersion);
        if (!toolCredentialsMap.has(key)) {
            toolCredentialsMap.set(key, useUserToolCredentials(toolId, toolVersion));
        }
    });

    // Helper function to get tool credentials by tool identifier
    const getToolCredentials = (toolId: string, toolVersion: string) => {
        const key = getToolKey(toolId, toolVersion);
        const credentials = toolCredentialsMap.get(key);
        if (!credentials) {
            throw new Error(
                `No credentials found for tool ${toolId}@${toolVersion}. Make sure it's included in the tools array.`
            );
        }
        return credentials;
    };

    // Aggregated computed properties
    const sourceCredentialsDefinitions = computed(() => {
        const definitions = new Map();
        toolCredentialsMap.forEach((credentials, key) => {
            definitions.set(key, credentials.sourceCredentialsDefinition.value);
        });
        return definitions;
    });

    const hasSomeOptionalCredentials = computed(() => {
        const map = new Map<string, boolean>();
        toolCredentialsMap.forEach((credentials, key) => {
            map.set(key, credentials.hasSomeOptionalCredentials.value);
        });
        return map;
    });

    const hasSomeRequiredCredentials = computed(() => {
        const map = new Map<string, boolean>();
        toolCredentialsMap.forEach((credentials, key) => {
            map.set(key, credentials.hasSomeRequiredCredentials.value);
        });
        return map;
    });

    const hasAnyCredentials = computed(() => {
        const map = new Map<string, boolean>();
        toolCredentialsMap.forEach((credentials, key) => {
            map.set(key, credentials.hasAnyCredentials.value);
        });
        return map;
    });

    const servicesCount = computed(() => {
        const map = new Map<string, number>();
        toolCredentialsMap.forEach((credentials, key) => {
            map.set(key, credentials.servicesCount.value);
        });
        return map;
    });

    const currentUserToolCredentials = computed(() => {
        const map = new Map<string, UserCredentials[] | undefined>();
        toolCredentialsMap.forEach((credentials, key) => {
            map.set(key, credentials.currentUserToolCredentials.value);
        });
        return map;
    });

    const mutableUserCredentials = computed(() => {
        const map = new Map<string, UserCredentials[] | undefined>();
        toolCredentialsMap.forEach((credentials, key) => {
            map.set(key, credentials.mutableUserCredentials.value);
        });
        return map;
    });

    const mutableUserCredentialsFor = computed(() => (toolId: string, toolVersion: string) => {
        const key = getToolKey(toolId, toolVersion);
        const credentials = toolCredentialsMap.get(key);
        if (!credentials) {
            throw new Error(
                `No mutable user credentials found for tool ${toolId}@${toolVersion}. Make sure it's included in the tools array.`
            );
        }
        return credentials.mutableUserCredentials.value;
    });

    const isBusy = computed(() => {
        const map = new Map<string, boolean>();
        toolCredentialsMap.forEach((credentials, key) => {
            map.set(key, credentials.isBusy.value);
        });
        return map;
    });

    const isAnyBusy = computed(() => {
        return Array.from(toolCredentialsMap.values()).some((credentials) => credentials.isBusy.value);
    });

    const busyMessage = computed(() => {
        const map = new Map<string, string>();
        toolCredentialsMap.forEach((credentials, key) => {
            map.set(key, credentials.busyMessage.value);
        });
        return map;
    });

    const statusVariant = computed(() => {
        const map = new Map<string, string>();
        toolCredentialsMap.forEach((credentials, key) => {
            map.set(key, credentials.statusVariant.value);
        });
        return map;
    });

    const hasUserProvidedRequiredCredentials = computed(() => {
        const map = new Map<string, boolean>();
        toolCredentialsMap.forEach((credentials, key) => {
            map.set(key, credentials.hasUserProvidedRequiredCredentials.value);
        });
        return map;
    });

    const hasUserProvidedAllCredentials = computed(() => {
        const map = new Map<string, boolean>();
        toolCredentialsMap.forEach((credentials, key) => {
            map.set(key, credentials.hasUserProvidedAllCredentials.value);
        });
        return map;
    });

    const provideCredentialsButtonTitle = computed(() => {
        const map = new Map<string, string>();
        toolCredentialsMap.forEach((credentials, key) => {
            map.set(key, credentials.provideCredentialsButtonTitle.value);
        });
        return map;
    });

    const isAnyToolBusy = computed(() => {
        return Array.from(toolCredentialsMap.values()).some((credentials) => credentials.isBusy.value);
    });

    const areAllToolsReady = computed(() => {
        return Array.from(toolCredentialsMap.values()).every(
            (credentials) => credentials.hasUserProvidedRequiredCredentials.value
        );
    });

    const areAllToolsFullyConfigured = computed(() => {
        return Array.from(toolCredentialsMap.values()).every(
            (credentials) => credentials.hasUserProvidedAllCredentials.value
        );
    });

    // Methods that work with specific tools
    async function checkUserCredentials(toolId: string, toolVersion: string) {
        const credentials = getToolCredentials(toolId, toolVersion);
        return await credentials.checkUserCredentials();
    }

    async function saveUserCredentials(
        toolId: string,
        toolVersion: string,
        providedCredentials: CreateSourceCredentialsPayload
    ) {
        const credentials = getToolCredentials(toolId, toolVersion);
        return await credentials.saveUserCredentials(providedCredentials);
    }

    async function deleteCredentialsGroup(
        toolId: string,
        toolVersion: string,
        serviceIdentifier: ServiceCredentialsIdentifier,
        groupName: string
    ) {
        const credentials = getToolCredentials(toolId, toolVersion);
        return await credentials.deleteCredentialsGroup(serviceIdentifier, groupName);
    }

    function refreshMutableCredentials(toolId: string, toolVersion: string) {
        const credentials = getToolCredentials(toolId, toolVersion);
        return credentials.refreshMutableCredentials();
    }

    function getServiceCredentialsDefinition(
        toolId: string,
        toolVersion: string,
        serviceIdentifier: ServiceCredentialsIdentifier
    ) {
        const credentials = getToolCredentials(toolId, toolVersion);
        return credentials.getServiceCredentialsDefinition(serviceIdentifier);
    }

    // Bulk operations
    async function checkAllUserCredentials() {
        const promises = Array.from(toolCredentialsMap.values()).map((credentials) =>
            credentials.checkUserCredentials()
        );
        return await Promise.all(promises);
    }

    function refreshAllMutableCredentials() {
        toolCredentialsMap.forEach((credentials) => {
            credentials.refreshMutableCredentials();
        });
    }

    // Helper methods for accessing data
    function getProperty<K extends keyof ReturnType<typeof useUserToolCredentials>>(
        toolId: string,
        toolVersion: string,
        property: K
    ): ReturnType<typeof useUserToolCredentials>[K] {
        const credentials = getToolCredentials(toolId, toolVersion);
        return credentials[property];
    }

    return {
        // Maps of properties indexed by tool key
        sourceCredentialsDefinitions,
        hasSomeOptionalCredentials,
        hasSomeRequiredCredentials,
        hasAnyCredentials,
        servicesCount,
        currentUserToolCredentials,
        mutableUserCredentials,
        mutableUserCredentialsFor,
        isBusy,
        busyMessage,
        statusVariant,
        hasUserProvidedRequiredCredentials,
        hasUserProvidedAllCredentials,
        provideCredentialsButtonTitle,

        // Aggregated state
        isAnyBusy,
        areAllToolsReady,
        areAllToolsFullyConfigured,

        // Methods for specific tools
        checkUserCredentials,
        saveUserCredentials,
        deleteCredentialsGroup,
        refreshMutableCredentials,
        getServiceCredentialsDefinition,

        // Bulk operations
        checkAllUserCredentials,
        refreshAllMutableCredentials,

        // Helper methods
        getToolKey,
        getProperty,
        getToolCredentials,
    };
}
