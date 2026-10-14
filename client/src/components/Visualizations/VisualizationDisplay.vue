<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import type { NavigationGuard } from "vue-router";
import { onBeforeRouteLeave, onBeforeRouteUpdate } from "vue-router";

import { GalaxyApi, isRegisteredUser } from "@/api";
import { useUserStore } from "@/stores/userStore";

import GAlert from "@/components/BaseComponents/GAlert.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import VisualizationFrame from "@/components/Visualizations/VisualizationFrame.vue";

export interface Props {
    datasetId?: string;
    visualization: string;
    visualizationId?: string;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "load"): void;
}>();

const { currentUser } = storeToRefs(useUserStore());

const errorMessage = ref<string>("");
const isLoading = ref<boolean>(true);
const hasUnsavedChanges = ref<boolean>(false);
const visualizationConfig = ref();
const visualizationTitle = ref<string | undefined>();
// Only an owner can save in place; for anyone else the plugin creates their own copy.
const ownedVisualizationId = ref<string | undefined>();

// Remount the iframe when its visualization identity changes.
const frameKey = computed(() => `${props.visualization}:${props.visualizationId ?? props.datasetId}`);

function handleLoad() {
    isLoading.value = false;
    emit("load");
}

function handleSaved(saved: boolean) {
    hasUnsavedChanges.value = !saved;
}

function onUnload(e: BeforeUnloadEvent) {
    if (hasUnsavedChanges.value) {
        e.preventDefault();
        e.returnValue = "";
    }
}

const confirmDiscard: NavigationGuard = () => {
    if (hasUnsavedChanges.value && !window.confirm("Unsaved changes will be lost. Continue?")) {
        return false;
    }
};

onBeforeRouteLeave(confirmDiscard);
// Switching tab or dataset keeps the same route record, so it arrives as an update.
onBeforeRouteUpdate(confirmDiscard);

onMounted(async () => {
    window.addEventListener("beforeunload", onUnload);
    if (props.visualizationId) {
        const { data, error } = await GalaxyApi().GET("/api/visualizations/{id}", {
            params: { path: { id: props.visualizationId } },
        });
        if (error) {
            errorMessage.value = error.err_msg;
        } else if (data?.latest_revision?.config) {
            visualizationConfig.value = data.latest_revision.config;
            visualizationTitle.value = data.title;
            const owner = isRegisteredUser(currentUser.value) && data.user_id === currentUser.value.id;
            ownedVisualizationId.value = owner ? props.visualizationId : undefined;
        } else {
            errorMessage.value = "Failed to access visualization details.";
        }
    } else {
        visualizationConfig.value = { dataset_id: props.datasetId };
    }
});

onBeforeUnmount(() => window.removeEventListener("beforeunload", onUnload));
</script>

<template>
    <div class="position-relative h-100 overflow-hidden">
        <GAlert v-if="errorMessage" variant="danger" show>
            {{ errorMessage }}
        </GAlert>
        <div v-else-if="isLoading" class="iframe-loading bg-light">
            <LoadingSpan message="Loading visualization" />
        </div>

        <VisualizationFrame
            v-if="visualizationConfig"
            :key="frameKey"
            :config="visualizationConfig"
            :name="props.visualization"
            :title="visualizationTitle"
            :visualization-id="ownedVisualizationId"
            @saved="handleSaved"
            @load="handleLoad" />
    </div>
</template>
