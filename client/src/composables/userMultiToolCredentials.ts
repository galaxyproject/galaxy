import { storeToRefs } from "pinia";
import { computed, reactive } from "vue";

import type { ToolIdentifier } from "@/api/tools";
import { getToolKey } from "@/api/tools";
import type { SelectCurrentGroupPayload, ServiceCredentialsIdentifier } from "@/api/users";
import { useUserToolCredentials } from "@/composables/userToolCredentials";
import { useUserToolsServiceCredentialsStore } from "@/stores/userToolsServiceCredentialsStore";

export function useUserMultiToolCredentials(tools: ToolIdentifier[]) {
    const userToolCredentialsByKey = reactive(new Map<string, ReturnType<typeof useUserToolCredentials>>());

    const { isBusy } = storeToRefs(useUserToolsServiceCredentialsStore());

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

    const someToolsHasRequiredServiceCredentials = computed(() => {
        return Array.from(userToolCredentialsByKey.values()).some(
            (userToolCredentials) => userToolCredentials.toolHasRequiredServiceCredentials.value
        );
    });

    const hasUserProvidedAllToolsServiceCredentials = computed(() => {
        return Array.from(userToolCredentialsByKey.values()).every(
            (userToolCredentials) => userToolCredentials.hasUserProvidedAllServiceCredentials.value
        );
    });

    const hasUserProvidedAllRequiredToolsServiceCredentials = computed(() => {
        return Array.from(userToolCredentialsByKey.values()).every(
            (userToolCredentials) => userToolCredentials.hasUserProvidedAllRequiredServiceCredentials.value
        );
    });

    const hasUserProvidedSomeOptionalToolsServiceCredentials = computed(() => {
        return Array.from(userToolCredentialsByKey.values()).some(
            (userToolCredentials) => userToolCredentials.hasUserProvidedSomeOptionalServiceCredentials.value
        );
    });

    // const statusVariant = computed<"success" | "info" | "warning">(() => {
    //     const map = new Map<string, string>();
    //     userToolCredentialsByKey.forEach((userToolCredentials, key) => {
    //         map.set(key, userToolCredentials.statusVariant.value);
    //     });

    //     if (Array.from(map.values()).every((v) => v === "success")) {
    //         return "success";
    //     } else if (Array.from(map.values()).some((v) => v === "info")) {
    //         return "info";
    //     }
    //     return "warning";
    // });

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
        return "warning";
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
