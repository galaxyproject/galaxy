import { defineStore } from "pinia";
import { computed, ref } from "vue";

import { getToolKey } from "@/api/tools";
import type { ServiceCredentialsDefinition, ServiceCredentialsIdentifier } from "@/api/users";

export const useToolsServiceCredentialsDefinitionsStore = defineStore("toolsServiceCredentialsDefinitionsStore", () => {
    const toolsServiceCredentialsDefinitions = ref<{ [key: string]: ServiceCredentialsDefinition[] }>({});

    const getToolServiceCredentialsDefinitionsFor = computed(() => {
        return (toolId: string, toolVersion: string): ServiceCredentialsDefinition[] => {
            const definitions = toolsServiceCredentialsDefinitions.value[getToolKey(toolId, toolVersion)];
            return definitions ?? [];
        };
    });

    function setToolServiceCredentialsDefinitionFor(
        toolId: string,
        toolVersion: string,
        serviceDefinitions: ServiceCredentialsDefinition[]
    ) {
        const toolKey = getToolKey(toolId, toolVersion);
        const existingDefinitions = toolsServiceCredentialsDefinitions.value[toolKey] || [];
        const uniqueDefinitions = serviceDefinitions.filter(
            (newDef) =>
                !existingDefinitions.some(
                    (existing) => existing.name === newDef.name && existing.version === newDef.version
                )
        );
        toolsServiceCredentialsDefinitions.value[toolKey] = [...existingDefinitions, ...uniqueDefinitions];
    }

    function getToolServiceCredentialsDefinitionFor(
        toolId: string,
        toolVersion: string,
        serviceCredentialsIdentifier: ServiceCredentialsIdentifier
    ): ServiceCredentialsDefinition | undefined {
        const definition = getToolServiceCredentialsDefinitionsFor
            .value(toolId, toolVersion)
            .find(
                (sd) =>
                    sd.name === serviceCredentialsIdentifier.name && sd.version === serviceCredentialsIdentifier.version
            );
        return definition;
    }

    return {
        toolsServiceCredentialsDefinitions,
        getToolServiceCredentialsDefinitionsFor,
        setToolServiceCredentialsDefinitionFor,
        getToolServiceCredentialsDefinitionFor,
    };
});
