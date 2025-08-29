import { defineStore } from "pinia";
import { ref } from "vue";

import { getToolKey } from "@/api/tools";
import type { ServiceCredentialsDefinition, ServiceCredentialsIdentifier } from "@/api/users";

export const useToolCredentialsDefinitionsStore = defineStore("toolCredentialsDefinitions", () => {
    const toolCredentialsDefinitions = ref<{ [key: string]: ServiceCredentialsDefinition[] }>({});

    function setToolCredentialsDefinition(
        toolId: string,
        toolVersion: string,
        serviceDefinitions: ServiceCredentialsDefinition[]
    ) {
        toolCredentialsDefinitions.value[getToolKey(toolId, toolVersion)] = serviceDefinitions;
    }

    function getToolCredentialsDefinitions(toolId: string, toolVersion: string): ServiceCredentialsDefinition[] {
        const definitions = toolCredentialsDefinitions.value[getToolKey(toolId, toolVersion)];
        if (!definitions) {
            throw new Error(`No credentials definitions found for tool ${getToolKey(toolId, toolVersion)}`);
        }
        return definitions;
    }

    function getServiceCredentialsDefinition(
        toolId: string,
        toolVersion: string,
        serviceCredentialsIdentifier: ServiceCredentialsIdentifier
    ): ServiceCredentialsDefinition | undefined {
        return toolCredentialsDefinitions.value[getToolKey(toolId, toolVersion)]?.find(
            (sd) => sd.name === serviceCredentialsIdentifier.name && sd.version === serviceCredentialsIdentifier.version
        );
    }

    return {
        toolCredentialsDefinitions,
        setToolCredentialsDefinition,
        getToolCredentialsDefinitions,
        getServiceCredentialsDefinition,
    };
});
