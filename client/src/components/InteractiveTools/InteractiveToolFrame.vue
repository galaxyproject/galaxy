<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, onMounted, ref } from "vue";

import { useEntryPointStore } from "@/stores/entryPointStore";
import { useInteractiveToolsStore } from "@/stores/interactiveToolsStore";

export interface Props {
    entryId: string;
}

const props = defineProps<Props>();
const entryPointStore = useEntryPointStore();
const interactiveToolsStore = useInteractiveToolsStore();
const { entryPoints } = storeToRefs(entryPointStore);

const loading = ref(true);
const error = ref<string | null>(null);

// Find the entry point with the matching ID from the store
const entryPoint = computed(() => {
    return entryPoints.value.find((entry) => entry.id === props.entryId);
});

// Get the target URL from the entry point
const frameUrl = computed(() => {
    if (entryPoint.value) {
        return entryPoint.value.target;
    }
    return null;
});

onMounted(async () => {
    // Ensure we have the entry points loaded
    try {
        await interactiveToolsStore.getActiveTools();
        loading.value = false;
        if (!entryPoint.value) {
            error.value = "Interactive tool not found. It may have been stopped or expired.";
        }
    } catch (err) {
        loading.value = false;
        error.value = `Failed to load interactive tool: ${(err as Error).message}`;
    }
});
</script>

<template>
    <div class="interactive-tool-frame">
        <div v-if="loading" class="d-flex justify-content-center align-items-center h-100">
            <b-spinner label="Loading interactive tool..."></b-spinner>
        </div>
        <div v-else-if="error" class="alert alert-danger m-3">
            {{ error }}
        </div>
        <iframe
            v-else-if="frameUrl"
            id="galaxy_interactive_tool"
            :src="frameUrl"
            class="center-frame"
            frameborder="0"
            title="galaxy interactive tool frame"
            width="100%"
            height="100%" />
        <div v-else class="alert alert-danger m-3">No URL available for this interactive tool.</div>
    </div>
</template>

<style scoped>
.interactive-tool-frame {
    height: 100%;
    width: 100%;
}

.center-frame {
    border: none;
    display: block;
    height: 100%;
}
</style>
