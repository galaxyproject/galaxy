<script setup lang="ts">
import { computed, ref, toRef, onMounted, type Ref } from "vue";
import { Connection, useConnectionStore, type OutputTerminal } from "@/stores/workflowConnectionStore";
import { storeToRefs } from "pinia";
import type { TerminalPosition } from "@/stores/workflowEditorStateStore";
import type { OutputTerminals } from "./modules/terminals";
import { useDrawableConnection, setDrawableConnectionStyle } from "./composables/drawableConnection";
import { useAnimationFrame } from "@/composables/sensors/animationFrame";

const props = defineProps<{
    draggingConnection: TerminalPosition | null;
    draggingTerminal: OutputTerminals | null;
    transform: { x: number; y: number; k: number };
}>();

const canvas: Ref<HTMLCanvasElement | null> = ref(null);
const context = computed(() => canvas.value?.getContext("2d") ?? null);

const connectionStore = useConnectionStore();
const { connections } = storeToRefs(connectionStore);

const drawableConnections = computed(() => {
    return connections.value.map((c) => useDrawableConnection(c));
});

onMounted(() => {
    const element = canvas.value!;
    const style = getComputedStyle(element);

    setDrawableConnectionStyle({
        connectionColor: style.getPropertyValue("--connection-color"),
        connectionColorInvalid: style.getPropertyValue("--connection-color-invalid"),
    });
});

const drawableDraggingConnection = computed(() => {
    if (props.draggingConnection && props.draggingTerminal) {
        const connection = new Connection(
            {
                connectorType: "input",
                name: "draggingInput",
                stepId: -1,
            },
            props.draggingTerminal as unknown as OutputTerminal
        );

        return useDrawableConnection(connection, toRef(props, "draggingConnection"));
    } else {
        return null;
    }
});

useAnimationFrame(() => {
    const ctx = context.value;
    if (!ctx) {
        return;
    }

    ctx.canvas.width = ctx.canvas.offsetWidth;
    ctx.canvas.height = ctx.canvas.offsetHeight;

    ctx.resetTransform();
    ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
    ctx.translate(props.transform.x, props.transform.y);
    ctx.scale(props.transform.k, props.transform.k);

    drawableConnections.value.forEach((connection) => connection.draw(ctx));

    if (drawableDraggingConnection.value) {
        drawableDraggingConnection.value.draw(ctx);
    }
});
</script>

<template>
    <div class="workflow-edges">
        <canvas ref="canvas" class="workflow-edges-canvas"></canvas>
    </div>
</template>

<style lang="scss" scoped>
@import "~bootstrap/scss/_functions.scss";
@import "theme/blue.scss";

.workflow-edges-canvas {
    --connection-color: #{$brand-primary};
    --connection-color-invalid: #{$brand-warning};

    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    width: 100%;
    height: 100%;
}
</style>
