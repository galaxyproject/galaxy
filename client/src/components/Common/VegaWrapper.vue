<template>
    <div>
        <b-alert v-if="errorMessage" class="p-2" variant="danger" show>
            {{ errorMessage }}
        </b-alert>
        <div ref="chartContainer" :style="style" />
    </div>
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
const errorMessage = ref<string>("");

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
        errorMessage.value = "";
    } catch (e: any) {
        errorMessage.value = String(e);
    }
}

onMounted(embedChart);

watch(props, embedChart, { deep: true });
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
