<script setup lang="ts">
import { useEventListener } from "@vueuse/core";
import { computed, ref, watch } from "vue";

import { Transform } from "@/components/Workflow/Editor/modules/geometry";
import { useWorkflowStores } from "@/composables/workflowStores";

const props = defineProps<{
    transform: { x: number; y: number; k: number };
}>();

const { toolbarStore } = useWorkflowStores();

const inputCatcher = ref<HTMLDivElement>();
const events = ["pointerup", "pointerdown", "pointermove", "pointerleave"] as const;

const inverseCanvasTransform = computed(() =>
    new Transform()
        .translate([props.transform.x, props.transform.y])
        .scale([props.transform.k, props.transform.k])
        .inverse()
);

const zIndexLow = 0;
const zIndexHigh = 1500;

const zIndex = ref(zIndexHigh);

watch(
    () => toolbarStore.currentTool,
    () => {
        if (toolbarStore.currentTool === "boxSelect") {
            zIndex.value = zIndexLow;
        } else {
            zIndex.value = zIndexHigh;
        }
    }
);

toolbarStore.onInputCatcherEvent("pointerdown", () => {
    zIndex.value = zIndexHigh;
});

toolbarStore.onInputCatcherEvent("pointerup", () => {
    if (toolbarStore.currentTool === "boxSelect") {
        zIndex.value = zIndexLow;
    }
});

const style = computed(() => ({
    transform: `matrix(${inverseCanvasTransform.value.matrix.join(",")})`,
    "z-index": `${zIndex.value}`,
}));

let lastPosition = [0, 0] as [number, number];

useEventListener(inputCatcher, [...events], (event: PointerEvent) => {
    event.preventDefault();
    event.stopPropagation();
    const position = inverseCanvasTransform.value.apply([event.offsetX, event.offsetY]);
    const catcherEvent = {
        type: event.type as (typeof events)[number],
        position,
    };
    lastPosition = position;
    toolbarStore.emitInputCatcherEvent(event.type as (typeof events)[number], catcherEvent);
});

watch(
    () => toolbarStore.inputCatcherEnabled,
    () => {
        if (toolbarStore.inputCatcherEnabled) {
            toolbarStore.emitInputCatcherEvent("temporarilyDisabled", {
                type: "temporarilyDisabled",
                position: lastPosition,
            });
        }
    }
);
</script>

<template>
    <div
        v-if="toolbarStore.inputCatcherActive && toolbarStore.inputCatcherEnabled"
        ref="inputCatcher"
        class="input-catcher"
        :style="style"></div>
</template>

<style scoped lang="scss">
.input-catcher {
    position: absolute;
    top: 0;
    left: 0;
    transform-origin: top left;
    width: 100%;
    height: 100%;
    cursor: crosshair;
}
</style>
