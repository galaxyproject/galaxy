<template>
    <div ref="chartContainer" :style="style"></div>
</template>

<script setup lang="ts">
import { useResizeObserver } from "@vueuse/core";
import embed, { type VisualizationSpec } from "vega-embed";
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";

export interface VisSpec {
    spec: VisualizationSpec;
    fillWidth?: boolean;
}

const props = withDefaults(defineProps<VisSpec>(), {
    fillWidth: true,
});

const style = computed(() => {
    if (props.fillWidth) {
        return { width: "100%" };
    }
    return {};
});

const chartContainer = ref<HTMLDivElement | null>(null);
let vegaView: any;

async function embedChart() {
    try {
        if (vegaView) {
            vegaView.finalize();
        }
        if (chartContainer.value !== null) {
            const result = await embed(chartContainer.value, props.spec, { renderer: "svg" });
            vegaView = result.view;
        }
    } catch (e: any) {
        console.error(String(e));
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
