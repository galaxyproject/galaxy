import { defineStore } from "pinia";
import { computed, ref } from "vue";

import type { DatatypeVisualization } from "@/api/datatypeVisualizations";
import {
    deleteDatatypeVisualization,
    fetchDatatypeVisualizations,
    getPreferredVisualization,
    updateDatatypeVisualization,
} from "@/api/datatypeVisualizations";

export const useDatatypeVisualizationsStore = defineStore("datatypeVisualizations", () => {
    const visualizationMappings = ref<DatatypeVisualization[]>([]);
    const loadingStates = ref<Record<string, boolean>>({});
    const errorStates = ref<Record<string, string>>({});

    // Computed maps for quick lookups
    const mappingByDatatype = computed(() => {
        const result: Record<string, DatatypeVisualization> = {};
        visualizationMappings.value.forEach((mapping) => {
            result[mapping.datatype] = mapping;
        });
        return result;
    });

    /**
     * Load all datatype visualization mappings
     */
    async function loadAllMappings() {
        loadingStates.value["all"] = true;
        errorStates.value["all"] = "";

        try {
            visualizationMappings.value = await fetchDatatypeVisualizations();
        } catch (error) {
            errorStates.value["all"] = error instanceof Error ? error.message : String(error);
        } finally {
            loadingStates.value["all"] = false;
        }
    }

    /**
     * Get the preferred visualization for a specific datatype
     */
    async function getPreferredVisualizationForDatatype(datatype: string): Promise<DatatypeVisualization | null> {
        // First check our store
        if (mappingByDatatype.value[datatype]) {
            return mappingByDatatype.value[datatype];
        }

        // If not in store, query the API
        loadingStates.value[datatype] = true;
        errorStates.value[datatype] = "";

        try {
            const result = await getPreferredVisualization(datatype);

            // If found, add to our store
            if (result) {
                visualizationMappings.value.push(result);
            }

            return result;
        } catch (error) {
            errorStates.value[datatype] = error instanceof Error ? error.message : String(error);
            return null;
        } finally {
            loadingStates.value[datatype] = false;
        }
    }

    /**
     * Update a visualization mapping
     */
    async function updateMapping(mapping: DatatypeVisualization) {
        loadingStates.value[mapping.datatype] = true;
        errorStates.value[mapping.datatype] = "";

        try {
            const updatedMapping = await updateDatatypeVisualization(mapping);

            // Update in our store
            const index = visualizationMappings.value.findIndex((m) => m.datatype === mapping.datatype);
            if (index >= 0) {
                visualizationMappings.value[index] = updatedMapping;
            } else {
                visualizationMappings.value.push(updatedMapping);
            }

            return updatedMapping;
        } catch (error) {
            errorStates.value[mapping.datatype] = error instanceof Error ? error.message : String(error);
            throw error;
        } finally {
            loadingStates.value[mapping.datatype] = false;
        }
    }

    /**
     * Delete a visualization mapping
     */
    async function deleteMapping(datatype: string) {
        loadingStates.value[datatype] = true;
        errorStates.value[datatype] = "";

        try {
            await deleteDatatypeVisualization(datatype);

            // Remove from our store
            visualizationMappings.value = visualizationMappings.value.filter((m) => m.datatype !== datatype);
        } catch (error) {
            errorStates.value[datatype] = error instanceof Error ? error.message : String(error);
            throw error;
        } finally {
            loadingStates.value[datatype] = false;
        }
    }

    return {
        visualizationMappings,
        loadingStates,
        errorStates,
        mappingByDatatype,
        loadAllMappings,
        getPreferredVisualizationForDatatype,
        updateMapping,
        deleteMapping,
    };
});
