import axios from "axios";
import { defineStore } from "pinia";
import { computed, ref } from "vue";

import { getAppRoot } from "@/onload/loadConfig";
import { useEntryPointStore } from "@/stores/entryPointStore";
import { rethrowSimple } from "@/utils/simple-error";

export const useInteractiveToolsStore = defineStore("interactiveToolsStore", () => {
    const entryPointStore = useEntryPointStore();
    const messages = ref<string[]>([]);

    /**
     * Stops an interactive tool by making a DELETE request to the API
     * and removes it from the entry points store if successful
     */
    async function stopInteractiveTool(id: string, name?: string) {
        try {
            const url = `${getAppRoot()}api/entry_points/${id}`;
            await axios.delete(url);
            entryPointStore.removeEntryPoint(id);
            return true;
        } catch (error) {
            const errorMessage = `Failed to stop interactive tool ${name || id}: ${(error as Error).message}`;
            messages.value.push(errorMessage);
            rethrowSimple(error);
            return false;
        }
    }

    /**
     * Clear all error messages
     */
    function clearMessages() {
        messages.value = [];
    }

    /**
     * Fetch active entry points from the entryPointStore
     */
    function getActiveTools() {
        return entryPointStore.fetchEntryPoints();
    }

    /**
     * Computed property to get active tools from the entryPointStore
     */
    const activeTools = computed(() => {
        return entryPointStore.entryPoints;
    });

    return {
        messages,
        activeTools,
        stopInteractiveTool,
        clearMessages,
        getActiveTools,
    };
});
