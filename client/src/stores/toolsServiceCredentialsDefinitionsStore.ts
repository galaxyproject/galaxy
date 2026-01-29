import { defineStore } from "pinia";
import { computed, ref } from "vue";

import { getToolKey } from "@/api/tools";
import type { ServiceCredentialsDefinition, ServiceCredentialsIdentifier } from "@/api/userCredentials";

/**
 * Pinia store for managing service credentials definitions for tools.
 * Handles storage and retrieval of tool-specific service credential definitions.
 */
export const useToolsServiceCredentialsDefinitionsStore = defineStore("toolsServiceCredentialsDefinitionsStore", () => {
    /** Service credentials definitions mapped by tool key. */
    const toolsServiceCredentialsDefinitions = ref<{ [key: string]: ServiceCredentialsDefinition[] }>({});

    /** Gets service credentials definitions for a specific tool and version. */
    const getToolServiceCredentialsDefinitionsFor = computed(() => {
        /**
         * Gets service credentials definitions for a specific tool and version.
         * @param {string} toolId - Tool identifier.
         * @param {string} toolVersion - Tool version.
         * @returns {ServiceCredentialsDefinition[]} Array of service credentials definitions.
         */
        return (toolId: string, toolVersion: string): ServiceCredentialsDefinition[] => {
            const definitions = toolsServiceCredentialsDefinitions.value[getToolKey(toolId, toolVersion)];
            return definitions ?? [];
        };
    });

    /**
     * Sets service credentials definitions for a specific tool, avoiding duplicates.
     * @param {string} toolId - Tool identifier.
     * @param {string} toolVersion - Tool version.
     * @param {ServiceCredentialsDefinition[]} serviceDefinitions - Array of service definitions to add.
     * @returns {void}
     */
    function setToolServiceCredentialsDefinitionFor(
        toolId: string,
        toolVersion: string,
        serviceDefinitions: ServiceCredentialsDefinition[],
    ): void {
        const toolKey = getToolKey(toolId, toolVersion);
        const existingDefinitions = toolsServiceCredentialsDefinitions.value[toolKey] || [];
        const uniqueDefinitions = serviceDefinitions.filter(
            (newDef) =>
                !existingDefinitions.some(
                    (existing) => existing.name === newDef.name && existing.version === newDef.version,
                ),
        );
        toolsServiceCredentialsDefinitions.value[toolKey] = [...existingDefinitions, ...uniqueDefinitions];
    }

    /**
     * Gets a specific service credentials definition by identifier.
     * @param {string} toolId - Tool identifier.
     * @param {string} toolVersion - Tool version.
     * @param {ServiceCredentialsIdentifier} serviceCredentialsIdentifier - Service name and version identifier.
     * @returns {ServiceCredentialsDefinition | undefined} Service definition or undefined if not found.
     */
    function getToolServiceCredentialsDefinitionFor(
        toolId: string,
        toolVersion: string,
        serviceCredentialsIdentifier: ServiceCredentialsIdentifier,
    ): ServiceCredentialsDefinition | undefined {
        const definition = getToolServiceCredentialsDefinitionsFor
            .value(toolId, toolVersion)
            .find(
                (sd) =>
                    sd.name === serviceCredentialsIdentifier.name &&
                    sd.version === serviceCredentialsIdentifier.version,
            );
        return definition;
    }

    /**
     * Gets the display label for a service credentials definition.
     * @param {string} toolId - Tool identifier.
     * @param {string} toolVersion - Tool version.
     * @param {ServiceCredentialsIdentifier} serviceIdentifier - Service name and version identifier.
     * @returns {string | undefined} Service label, name, or undefined if not found.
     */
    function getToolServiceCredentialsDefinitionLabelFor(
        toolId: string,
        toolVersion: string,
        serviceIdentifier: ServiceCredentialsIdentifier,
    ): string | undefined {
        const definition = getToolServiceCredentialsDefinitionFor(toolId, toolVersion, serviceIdentifier);
        return definition?.label || definition?.name;
    }

    return {
        toolsServiceCredentialsDefinitions,
        getToolServiceCredentialsDefinitionsFor,
        setToolServiceCredentialsDefinitionFor,
        getToolServiceCredentialsDefinitionFor,
        getToolServiceCredentialsDefinitionLabelFor,
    };
});
