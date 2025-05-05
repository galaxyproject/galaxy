<template>
    <div>
        <b-alert v-if="errorMessage" class="p-2" variant="danger" show>
            {{ errorMessage }}
        </b-alert>
        <div ref="chartContainer" :class="fillWidth && 'w-100'" />
    </div>
</template>

<script setup lang="ts">
import { useResizeObserver } from "@vueuse/core";
import embed, { type VisualizationSpec } from "vega-embed";
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";

export interface VisSpec {
    spec: VisualizationSpec;
    fillWidth?: boolean;
}

const props = withDefaults(defineProps<VisSpec>(), {
    fillWidth: true,
});

const chartContainer = ref<HTMLDivElement | null>(null);
const errorMessage = ref<string>("");

let vegaView: any;

async function embedChart() {
    try {
        await nextTick();
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

watch(props, embedChart, { deep: true });

useResizeObserver(chartContainer, () => {
    if (vegaView) {
        vegaView.resize();
    }
});

onMounted(() => embedChart());

// Cleanup the chart when the component is unmounted
onBeforeUnmount(() => {
    if (vegaView) {
        vegaView.finalize();
    }
});
</script>
