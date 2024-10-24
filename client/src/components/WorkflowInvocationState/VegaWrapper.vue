<template>
    <div ref="chartContainer" class="chart"></div>
</template>

<script setup lang="ts">
import embed, { type VisualizationSpec } from "vega-embed";
import { onBeforeUnmount, onMounted, ref, watch } from "vue";

export interface VisSpec {
    spec: VisualizationSpec;
}

const props = defineProps<VisSpec>();

const chartContainer = ref<HTMLDivElement | null>(null);
let vegaView: any;

watch(
    props,
    async () => {
        console.log(props.spec);
        if (chartContainer.value) {
            const result = await embed(chartContainer.value, props.spec);
            vegaView = result.view;
        }
    },
    { immediate: true }
);

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
    height: 300rem;
}
</style>
