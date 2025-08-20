import { defineStore } from "pinia";
import { ref } from "vue";

import type { ServiceCredentialsDefinition, ServiceCredentialsIdentifier } from "@/api/users";

export const useToolCredentialsDefinitionsStore = defineStore("toolCredentialsDefinitions", () => {
    const toolCredentialsDefinitions = ref<{ [key: string]: ServiceCredentialsDefinition[] }>({});

    function setToolCredentialsDefinition(
        toolId: string,
        toolVersion: string,
        serviceDefinitions: ServiceCredentialsDefinition[]
    ) {
        toolCredentialsDefinitions.value[`${toolId}:${toolVersion}`] = serviceDefinitions;
    }

    function getToolCredentialsDefinitions(
        toolId: string,
        toolVersion: string
    ): ServiceCredentialsDefinition[] | undefined {
        return toolCredentialsDefinitions.value[`${toolId}:${toolVersion}`];
    }

    function getServiceCredentialsDefinition(
        toolId: string,
        toolVersion: string,
        serviceCredentialsIdentifier: ServiceCredentialsIdentifier
    ): ServiceCredentialsDefinition | undefined {
        return toolCredentialsDefinitions.value[`${toolId}:${toolVersion}`]?.find(
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
