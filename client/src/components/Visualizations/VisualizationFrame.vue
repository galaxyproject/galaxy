<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { onBeforeRouteLeave } from "vue-router/composables";

import { withPrefix } from "@/utils/redirect";

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

const srcWithRoot = computed(() => {
    let url = "";
    if (props.visualization === "trackster") {
        if (props.visualizationId) {
            url = `/visualization/trackster?id=${props.visualizationId}`;
        } else {
            url = `/visualization/trackster?dataset_id=${props.datasetId}`;
        }
    } else {
        if (props.visualizationId) {
            url = `/plugins/visualizations/${props.visualization}/saved?id=${props.visualizationId}`;
        } else {
            const query = props.datasetId ? `?dataset_id=${props.datasetId}` : "";
            url = `/plugins/visualizations/${props.visualization}/show${query}`;
        }
    }

    return withPrefix(url);
});

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

onMounted(() => {
    window.addEventListener("beforeunload", (e) => {
        if (hasUnsavedChanges.value) {
            e.preventDefault();
            e.returnValue = "";
        }
    });
});
</script>

<template>
    <div class="position-relative h-100">
        <div v-if="isLoading" class="iframe-loading bg-light">
            <LoadingSpan message="Loading preview" />
        </div>
        <iframe
            id="galaxy_visualization"
            ref="iframeRef"
            :src="srcWithRoot"
            class="center-frame"
            frameborder="0"
            title="galaxy visualization frame"
            width="100%"
            height="100%"
            @load="handleLoad" />
    </div>
</template>

<style>
.iframe-loading {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    z-index: 10;
    opacity: 0.9;
    pointer-events: none;
}
</style>
