<template>
    <div ref="chartContainer" class="chart"></div>
</template>

<script setup lang="ts">
import { useResizeObserver } from "@vueuse/core";
import embed, { type VisualizationSpec } from "vega-embed";
import { onBeforeUnmount, onMounted, ref, watch } from "vue";

export interface VisSpec {
    spec: VisualizationSpec;
}

const props = defineProps<VisSpec>();

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
    embedChart();
});

// Cleanup the chart when the component is unmounted
onBeforeUnmount(() => {
    if (vegaView) {
        vegaView.finalize();
    }
});
</script>

<style scoped>
.chart {
    width: 100%;
    height: 100%;
}
</style>
