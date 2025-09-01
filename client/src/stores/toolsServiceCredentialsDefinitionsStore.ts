import { defineStore } from "pinia";
import { ref } from "vue";

import { getToolKey } from "@/api/tools";
import type { ServiceCredentialsDefinition, ServiceCredentialsIdentifier } from "@/api/users";

export const useToolsServiceCredentialsDefinitionsStore = defineStore("toolsServiceCredentialsDefinitionsStore", () => {
    const toolsServiceCredentialsDefinitions = ref<{ [key: string]: ServiceCredentialsDefinition[] }>({});

    function setToolServiceCredentialsDefinitionFor(
        toolId: string,
        toolVersion: string,
        serviceDefinitions: ServiceCredentialsDefinition[]
    ) {
        toolsServiceCredentialsDefinitions.value[getToolKey(toolId, toolVersion)] = serviceDefinitions;
    }

    function getToolServiceCredentialsDefinitionsFor(
        toolId: string,
        toolVersion: string
    ): ServiceCredentialsDefinition[] {
        const definitions = toolsServiceCredentialsDefinitions.value[getToolKey(toolId, toolVersion)];
        if (!definitions) {
            throw new Error(`No service credentials definitions found for tool: ${getToolKey(toolId, toolVersion)}`);
        }
        return definitions;
    }

    function getToolServiceCredentialsDefinitionFor(
        toolId: string,
        toolVersion: string,
        serviceCredentialsIdentifier: ServiceCredentialsIdentifier
    ): ServiceCredentialsDefinition | undefined {
        const definition = getToolServiceCredentialsDefinitionsFor(toolId, toolVersion).find(
            (sd) => sd.name === serviceCredentialsIdentifier.name && sd.version === serviceCredentialsIdentifier.version
        );
        return definition;
    }

    return {
        toolsServiceCredentialsDefinitions,
        setToolServiceCredentialsDefinitionFor,
        getToolServiceCredentialsDefinitionsFor,
        getToolServiceCredentialsDefinitionFor,
    };
});
