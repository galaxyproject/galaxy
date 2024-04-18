<script setup lang="ts">
import { computed } from "vue";

import { withPrefix } from "@/utils/redirect";

export interface Props {
    visualizationId: string;
    datasetId: string;
}

const props = defineProps<Props>();

const srcWithRoot = computed(() => {
    if (props.visualizationId === "trackster") {
        return withPrefix(`/visualization/${props.visualizationId}?id=${props.datasetId}`);
    } else {
        return withPrefix(`/plugins/visualizations/${props.visualizationId}/saved?id=${props.datasetId}`);
    }
});
</script>

<template>
    <iframe
        :src="srcWithRoot"
        class="center-frame"
        frameborder="0"
        title="galaxy visualization frame"
        width="100%"
        height="100%" />
</template>
