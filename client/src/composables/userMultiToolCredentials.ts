import { computed, reactive } from "vue";

import type { ToolIdentifier } from "@/api/tools";
import { getToolKey } from "@/api/tools";
import type { SelectCurrentGroupPayload, ServiceCredentialsIdentifier } from "@/api/users";
import { useUserToolCredentials } from "@/composables/userToolCredentials";

export function useUserMultiToolCredentials(tools: ToolIdentifier[]) {
    const userToolCredentialsByKey = reactive(new Map<string, ReturnType<typeof useUserToolCredentials>>());

    tools.forEach(({ toolId, toolVersion }) => {
        const toolKey = getToolKey(toolId, toolVersion);
        if (!userToolCredentialsByKey.has(toolKey)) {
            userToolCredentialsByKey.set(toolKey, useUserToolCredentials(toolId, toolVersion));
        }
    });

    const sourceCredentialsDefinitionFor = computed(() => (toolId: string, toolVersion: string) => {
        const toolKey = getToolKey(toolId, toolVersion);
        const userToolCredentials = userToolCredentialsByKey.get(toolKey);
        if (!userToolCredentials) {
            throw new Error(
                `No credentials found for tool ${getToolKey(
                    toolId,
                    toolVersion
                )}. Make sure it's included in the tools array.`
            );
        }
        return userToolCredentials.sourceCredentialsDefinition.value;
    });

    const userServiceForTool = computed(
        () => (toolId: string, toolVersion: string, sd: ServiceCredentialsIdentifier) => {
            const toolKey = getToolKey(toolId, toolVersion);
            const userToolCredentials = userToolCredentialsByKey.get(toolKey);
            return userToolCredentials?.userServiceFor.value(sd);
        }
    );

    const hasSomeToolWithOptionalCredentials = computed(() => {
        const map = new Map<string, boolean>();
        userToolCredentialsByKey.forEach((userToolCredentials, key) => {
            map.set(key, userToolCredentials.hasSomeOptionalCredentials.value);
        });
        return map;
    });

    const hasSomeToolWithRequiredCredentials = computed(() => {
        const map = new Map<string, boolean>();
        userToolCredentialsByKey.forEach((userToolCredentials, key) => {
            map.set(key, userToolCredentials.hasSomeRequiredCredentials.value);
        });
        return map;
    });

    const statusVariant = computed<"success" | "info" | "warning">(() => {
        const map = new Map<string, string>();
        userToolCredentialsByKey.forEach((userToolCredentials, key) => {
            map.set(key, userToolCredentials.statusVariant.value);
        });

        if (Array.from(map.values()).every((v) => v === "success")) {
            return "success";
        } else if (Array.from(map.values()).some((v) => v === "info")) {
            return "info";
        }
        return "warning";
    });

    const hasUserProvidedAllRequiredToolsCredentials = computed(() => {
        const map = new Map<string, boolean>();
        userToolCredentialsByKey.forEach((userToolCredentials, key) => {
            map.set(key, userToolCredentials.hasUserProvidedRequiredCredentials.value);
        });
        return map;
    });

    const hasUserProvidedAllToolsCredentials = computed(() => {
        const map = new Map<string, boolean>();
        userToolCredentialsByKey.forEach((userToolCredentials, key) => {
            map.set(key, userToolCredentials.hasUserProvidedAllCredentials.value);
        });
        return map;
    });

    async function checkAllUserCredentials() {
        const promises = Array.from(userToolCredentialsByKey.values()).map((c) => c.checkUserCredentials());
        return await Promise.all(promises);
    }

    function getToolCredentials(toolId: string, toolVersion: string) {
        const toolKey = getToolKey(toolId, toolVersion);
        const userToolCredentials = userToolCredentialsByKey.get(toolKey);
        if (!userToolCredentials) {
            throw new Error(
                `No credentials found for tool ${getToolKey(
                    toolId,
                    toolVersion
                )}. Make sure it's included in the tools array.`
            );
        }
        return userToolCredentials;
    }

    function selectCurrentCredentialsGroupsForTool(
        toolId: string,
        toolVersion: string,
        serviceCredentials: SelectCurrentGroupPayload[]
    ) {
        const toolCredentials = getToolCredentials(toolId, toolVersion);
        return toolCredentials.selectCurrentCredentialsGroups(serviceCredentials);
    }

    return {
        statusVariant,
        userServiceForTool,
        sourceCredentialsDefinitionFor,

        hasUserProvidedAllRequiredToolsCredentials,
        hasUserProvidedAllToolsCredentials,
        hasSomeToolWithOptionalCredentials,
        hasSomeToolWithRequiredCredentials,

        checkAllUserCredentials,
        selectCurrentCredentialsGroupsForTool,
    };
}
