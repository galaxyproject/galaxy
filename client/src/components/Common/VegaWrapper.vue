<template>
    <div ref="outerContainer">
        <b-alert v-if="errorMessage" class="p-2" variant="danger" show>
            {{ errorMessage }}
        </b-alert>
        <div ref="chartContainer" :class="fillWidth && 'w-100'" />
    </div>
</template>

<script setup lang="ts">
import { useResizeObserver } from "@vueuse/core";
import type { View } from "vega";
import embed, { type VisualizationSpec } from "vega-embed";
import { nextTick, onBeforeUnmount, onMounted, ref, toRaw, watch } from "vue";

interface Props {
    spec: VisualizationSpec;
    fillWidth?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    fillWidth: true,
});

const emit = defineEmits<{
    (e: "new-view", view: View): void;
}>();

const outerContainer = ref<HTMLDivElement | null>(null);
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
            const result = await embed(chartContainer.value, toRaw(props.spec), { renderer: "svg" });
            vegaView = result.view;
            emit("new-view", vegaView);
        }
        errorMessage.value = "";
    } catch (e: any) {
        errorMessage.value = String(e);
    }
}

watch(props, embedChart, { deep: true });

function onResize() {
    if (vegaView && outerContainer.value) {
        const containerWidth = outerContainer.value.clientWidth;
        vegaView.width(containerWidth).runAsync();
    }
}

useResizeObserver(outerContainer, onResize);

onMounted(() => embedChart());

onBeforeUnmount(() => {
    if (vegaView) {
        vegaView.finalize();
    }
});
</script>
