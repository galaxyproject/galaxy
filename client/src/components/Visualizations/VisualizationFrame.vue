<script setup lang="ts">
import { computed } from "vue";

import { withPrefix } from "@/utils/redirect";

export interface Props {
    datasetId?: string;
    visualization: string;
    visualizationId?: string;
}

const props = defineProps<Props>();

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
</script>

<template>
    <iframe
        id="galaxy_visualization"
        :src="srcWithRoot"
        class="center-frame"
        frameborder="0"
        title="galaxy visualization frame"
        width="100%"
        height="100%" />
</template>
