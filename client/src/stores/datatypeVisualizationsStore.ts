import { defineStore } from "pinia";
import { computed, ref } from "vue";

import type { DatatypeVisualization } from "@/api/datatypeVisualizations";
import { fetchDatatypeVisualizations, getPreferredVisualization } from "@/api/datatypeVisualizations";

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

    // Note: Update and delete operations removed as they're now configured via XML only

    return {
        visualizationMappings,
        loadingStates,
        errorStates,
        mappingByDatatype,
        loadAllMappings,
        getPreferredVisualizationForDatatype,
    };
});
