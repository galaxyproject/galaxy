<script setup lang="ts">
import { ref, computed } from "vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import { withPrefix } from "@/utils/redirect";

const emit = defineEmits(["load"]);

export interface Props {
    datasetId?: string;
    visualization: string;
    visualizationId?: string;
}

const props = defineProps<Props>();

const isLoading = ref(true);

const srcWithRoot = computed(() => {
    let url = "";
    if (props.visualization === "trackster") {
        if (props.datasetId) {
            url = `/visualization/trackster?dataset_id=${props.datasetId}`;
        } else {
            url = `/visualization/trackster?id=${props.visualizationId}`;
        }
    } else {
        if (props.datasetId) {
            url = `/plugins/visualizations/${props.visualization}/show?dataset_id=${props.datasetId}`;
        } else {
            url = `/plugins/visualizations/${props.visualization}/saved?id=${props.visualizationId}`;
        }
    }

    return withPrefix(url);
});

function handleLoad() {
    isLoading.value = false;
    emit("load");
}
</script>

<template>
    <div class="position-relative h-100">
        <div v-if="isLoading" class="iframe-loading bg-light">
            <LoadingSpan message="Loading preview" />
        </div>
        <iframe
            id="galaxy_visualization"
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