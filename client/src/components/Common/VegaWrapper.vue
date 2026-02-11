<template>
    <div>
        <b-alert v-if="errorMessage" class="p-2" variant="danger" show>
            {{ errorMessage }}
        </b-alert>
        <div ref="chartContainer" :class="fillWidth && 'w-100'" />
    </div>
</template>

<script setup lang="ts">
import { useDebounceFn, useResizeObserver } from "@vueuse/core";
import embed, { type VisualizationSpec } from "vega-embed";
import { nextTick, onBeforeUnmount, onMounted, ref, toRaw, watch } from "vue";
import type { View } from "vega";

const RESIZE_DEBOUNCE_MS = 150;

interface Props {
    spec: VisualizationSpec;
    fillWidth?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    fillWidth: true,
});

const chartContainer = ref<HTMLDivElement | null>(null);
const errorMessage = ref<string>("");

let vegaView: View | null = null;

async function embedChart() {
    try {
        await nextTick();
        if (vegaView) {
            vegaView.finalize();
        }
        if (chartContainer.value !== null) {
            const result = await embed(
                chartContainer.value,
                { ...toRaw(props.spec), width: "container", height: "container" } as VisualizationSpec,
                { renderer: "svg" },
            );
            vegaView = result.view;
        }
        errorMessage.value = "";
    } catch (e: any) {
        errorMessage.value = String(e);
    }
}

watch(props, embedChart, { deep: true });

const debouncedResize = useDebounceFn(() => {
    if (vegaView) {
        vegaView.resize().runAsync();
    }
}, RESIZE_DEBOUNCE_MS);

useResizeObserver(chartContainer, debouncedResize);

onMounted(() => embedChart());

onBeforeUnmount(() => {
    if (vegaView) {
        vegaView.finalize();
    }
});
</script>
