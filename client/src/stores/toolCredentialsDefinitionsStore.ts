import { defineStore } from "pinia";
import { ref } from "vue";

import type { ServiceCredentialsDefinition, ServiceCredentialsIdentifier } from "@/api/users";

export const useToolCredentialsDefinitionsStore = defineStore("toolCredentialsDefinitions", () => {
    const toolCredentialsDefinitions = ref<{ [key: string]: ServiceCredentialsDefinition[] }>({});

    function getKey(toolId: string, toolVersion: string): string {
        return `${toolId}:${toolVersion}`;
    }

    function setToolCredentialsDefinition(
        toolId: string,
        toolVersion: string,
        serviceDefinitions: ServiceCredentialsDefinition[]
    ) {
        toolCredentialsDefinitions.value[getKey(toolId, toolVersion)] = serviceDefinitions;
    }

    function getToolCredentialsDefinitions(toolId: string, toolVersion: string): ServiceCredentialsDefinition[] {
        const definitions = toolCredentialsDefinitions.value[getKey(toolId, toolVersion)];
        if (!definitions) {
            throw new Error(`No credentials definitions found for tool ${getKey(toolId, toolVersion)}`);
        }
        return definitions;
    }

    function getServiceCredentialsDefinition(
        toolId: string,
        toolVersion: string,
        serviceCredentialsIdentifier: ServiceCredentialsIdentifier
    ): ServiceCredentialsDefinition | undefined {
        return toolCredentialsDefinitions.value[getKey(toolId, toolVersion)]?.find(
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
