<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import type { NavigationGuard } from "vue-router";
import { onBeforeRouteLeave, onBeforeRouteUpdate } from "vue-router";

import { GalaxyApi, isRegisteredUser } from "@/api";
import { useUserStore } from "@/stores/userStore";
import { errorMessageAsString } from "@/utils/simple-error";

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

const userStore = useUserStore();
const { currentUser } = storeToRefs(userStore);

const errorMessage = ref<string>("");
const isLoading = ref<boolean>(true);
const hasUnsavedChanges = ref<boolean>(false);
const visualizationConfig = ref();
const visualizationTitle = ref<string | undefined>();
const visualizationOwnerId = ref<string | undefined>();
// Only an owner can save in place; for anyone else the plugin creates their own copy.
const ownedVisualizationId = computed(() =>
    isRegisteredUser(currentUser.value) && visualizationOwnerId.value === currentUser.value.id
        ? props.visualizationId
        : undefined,
);
// The frame reads the id once at mount, so a saved visualization waits until the viewer is known.
const showFrame = computed(
    () => Boolean(visualizationConfig.value) && (!props.visualizationId || currentUser.value !== null),
);

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

// Embedded views (iframe, ?embed=true) skip the app's user load, so the frame would wait forever.
async function loadViewer() {
    try {
        await userStore.loadUser(false);
    } catch (e) {
        // The load is shared with the app's, whose history load can fail after the viewer is already set.
        if (currentUser.value === null) {
            // Without the viewer an owner's save would create a copy, so show no frame at all.
            errorMessage.value = errorMessageAsString(e);
        }
    }
}

onMounted(async () => {
    window.addEventListener("beforeunload", onUnload);
    if (props.visualizationId) {
        loadViewer();
        const { data, error } = await GalaxyApi().GET("/api/visualizations/{id}", {
            params: { path: { id: props.visualizationId } },
        });
        if (error) {
            errorMessage.value = error.err_msg;
        } else if (data?.latest_revision?.config) {
            visualizationConfig.value = data.latest_revision.config;
            visualizationTitle.value = data.title;
            visualizationOwnerId.value = data.user_id;
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
            v-if="showFrame"
            :key="frameKey"
            :config="visualizationConfig"
            :name="props.visualization"
            :title="visualizationTitle"
            :visualization-id="ownedVisualizationId"
            @saved="handleSaved"
            @load="handleLoad" />
    </div>
</template>
