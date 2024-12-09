<template>
    <div ref="chartContainer" :style="style"></div>
</template>

<script setup lang="ts">
import { useResizeObserver } from "@vueuse/core";
import embed, { type VisualizationSpec } from "vega-embed";
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";

export interface VisSpec {
    spec: VisualizationSpec;
    width: string;
}

const props = withDefaults(defineProps<VisSpec>(), {
    width: "100%",
});

const style = computed(() => {
    return { width: props.width };
});

const chartContainer = ref<HTMLDivElement | null>(null);
let vegaView: any;

async function embedChart() {
    if (vegaView) {
        vegaView.finalize();
    }
    if (chartContainer.value !== null) {
        const result = await embed(chartContainer.value, props.spec, { renderer: "svg" });
        vegaView = result.view;
    }
}

onMounted(embedChart);

watch(props, embedChart, { immediate: true, deep: true });
useResizeObserver(chartContainer, () => {
    if (vegaView) {
        vegaView.resize();
    }
});

// Cleanup the chart when the component is unmounted
onBeforeUnmount(() => {
    if (vegaView) {
        vegaView.finalize();
    }
});
</script>
