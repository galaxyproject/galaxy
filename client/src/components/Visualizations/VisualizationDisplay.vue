<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { onMounted, ref } from "vue";
import { onBeforeRouteLeave } from "vue-router/composables";

import { GalaxyApi } from "@/api";

import VisualizationFrame from "./VisualizationFrame.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

const emit = defineEmits(["load"]);

export interface Props {
    datasetId?: string;
    visualization: string;
    visualizationId?: string;
}

const props = defineProps<Props>();

const errorMessage = ref("");
const iframeRef = ref<HTMLIFrameElement | null>(null);
const isLoading = ref(true);
const hasUnsavedChanges = ref(false);
const visualizationConfig = ref();

function handleLoad() {
    isLoading.value = false;
    emit("load");
    setupChangeDetection();
}

function setupChangeDetection() {
    const iframe = iframeRef.value;
    if (!iframe?.contentWindow) {
        return;
    }

    setTimeout(() => {
        try {
            const iframeDoc = iframe.contentDocument;
            if (!iframeDoc) {
                return;
            }

            const markAsChanged = () => {
                if (!hasUnsavedChanges.value) {
                    hasUnsavedChanges.value = true;
                }
            };

            // Monitor DOM changes (skip initial load)
            setTimeout(() => {
                const observer = new MutationObserver(() => markAsChanged());
                observer.observe(iframeDoc.body, {
                    childList: true,
                    subtree: true,
                    characterData: true,
                });
            }, 2000);

            // Monitor user input
            ["input", "change", "keyup", "paste"].forEach((type) => {
                iframeDoc.addEventListener(type, markAsChanged, true);
            });
        } catch (e) {
            console.warn("Cannot monitor iframe for changes:", e);
        }
    }, 1000);
}

onBeforeRouteLeave((to, from, next) => {
    if (hasUnsavedChanges.value && !window.confirm("Unsaved changes will be lost. Continue?")) {
        next(false);
    } else {
        next();
    }
});

onMounted(async () => {
    if (props.visualizationId) {
        const { data, error } = await GalaxyApi().GET("/api/visualizations/{id}", {
            params: { path: { id: props.visualizationId } },
        });
        if (error) {
            errorMessage.value = error.err_msg;
        } else if (data?.latest_revision?.config) {
            visualizationConfig.value = data.latest_revision.config;
            errorMessage.value = "";
        } else {
            errorMessage.value = "Failed to access visualization details.";
        }
    } else {
        visualizationConfig.value = { dataset_id: props.datasetId };
    }

    window.addEventListener("beforeunload", (e) => {
        if (hasUnsavedChanges.value) {
            e.preventDefault();
            e.returnValue = "";
        }
    });
});
</script>

<template>
    <div class="position-relative h-100 overflow-hidden">
        <BAlert v-if="errorMessage" variant="danger" show>
            {{ errorMessage }}
        </BAlert>
        <div v-else-if="isLoading" class="iframe-loading bg-light">
            <LoadingSpan message="Loading visualization" />
        </div>
        <VisualizationFrame
            v-if="visualizationConfig"
            :config="visualizationConfig"
            :name="visualization"
            @load="handleLoad" />
    </div>
</template>
