<script setup lang="ts">
import axios from "axios";
import { onMounted, ref } from "vue";
import { onBeforeRouteLeave } from "vue-router/composables";

import { withPrefix } from "@/utils/redirect";

import VisualizationWrapper from "./VisualizationWrapper.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

const emit = defineEmits(["load"]);

export interface Props {
    datasetId?: string;
    visualization: string;
    visualizationId?: string;
}

const props = defineProps<Props>();

const isLoading = ref(true);
const hasUnsavedChanges = ref(false);
const iframeRef = ref<HTMLIFrameElement | null>(null);
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
        const url = withPrefix(`/api/visualizations/${props.visualizationId}`);
        const { data } = await axios.get(url);
        console.log(data.latest_revision.config);
        visualizationConfig.value = data.latest_revision.config;
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
        <div v-if="isLoading" class="iframe-loading bg-light">
            <LoadingSpan message="Loading preview" />
        </div>
        <VisualizationWrapper
            v-if="visualizationConfig"
            :full-height="true"
            :config="visualizationConfig"
            :name="visualization"
            @load="handleLoad" />
    </div>
</template>
