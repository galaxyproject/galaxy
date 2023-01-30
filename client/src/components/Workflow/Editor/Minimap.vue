<script lang="ts" setup>
import { onMounted, ref, unref, watch } from "vue";
import { useAnimationFrame } from "@/composables/sensors/animationFrame";
import { useWorkflowStateStore } from "@/stores/workflowEditorStateStore";
import { AxisAlignedBoundingBox } from "./modules/geomerty";

import type { Step, Steps } from "@/stores/workflowStepStore";
import type { PropType, Ref, ToRefs } from "vue";

const props = defineProps({
    steps: {
        type: Object as PropType<Steps>,
        required: true,
    },
    viewportBounds: {
        type: Object as PropType<ToRefs<{ width: number; height: number }>>,
        required: true,
    },
    viewportPan: {
        type: Object as PropType<{ x: number; y: number }>,
        required: true,
    },
    viewportScale: {
        type: Number,
        required: true,
    },
});

const canvas: Ref<HTMLCanvasElement | null> = ref(null);
let redraw = false;
let aabbChanged = false;
const stateStore = useWorkflowStateStore();
const aabb = new AxisAlignedBoundingBox();

watch(props.viewportBounds, () => (redraw = true), { deep: true });

const colors = {
    node: "#000",
    error: "#000",
    selectedOutline: "#000",
    view: "#000",
    viewOutline: "#000",
};

onMounted(() => {
    const element = canvas.value!;
    const style = getComputedStyle(element);

    colors.node = style.getPropertyValue("--node-color");
    colors.error = style.getPropertyValue("--error-color");
    colors.selectedOutline = style.getPropertyValue("--selected-outline-color");
    colors.view = style.getPropertyValue("--view-color");
    colors.viewOutline = style.getPropertyValue("--view-outline-color");

    recalculateAABB();
    redraw = true;
});

watch(
    props.steps,
    () => {
        redraw = true;
        aabbChanged = true;
    },
    { deep: true }
);

watch(
    () => {
        props.viewportScale;
        props.viewportPan;
    },
    () => {
        redraw = true;
    },
    { deep: true }
);

function recalculateAABB() {
    aabb.reset();

    Object.values(props.steps).forEach((step) => {
        const rect = stateStore.stepPosition[step.id];
        aabb.fitRectangle({
            x: step.position!.left,
            y: step.position!.top,
            width: rect.width,
            height: rect.height,
        });
    });

    aabb.squareCenter();
    aabb.expand(20);
}

useAnimationFrame(() => {
    if (aabbChanged) {
        recalculateAABB();
        aabbChanged = false;
    }

    if (redraw && canvas.value) {
        renderMinimap();
        redraw = false;
    }
});

function renderMinimap() {
    const ctx = canvas.value!.getContext("2d") as CanvasRenderingContext2D;
    ctx.resetTransform();
    ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);

    // move ctx to aabb
    const scale = ctx.canvas.width / aabb.width;

    ctx.translate(-aabb.x * scale, -aabb.y * scale);
    ctx.scale(scale, scale);

    const allSteps = Object.values(props.steps);
    const okSteps: Step[] = [];
    const errorSteps: Step[] = [];
    let selectedStep: Step | undefined;

    allSteps.forEach((step) => {
        if (stateStore.activeNodeId === step.id) {
            selectedStep = step;
        }

        if (step.errors) {
            errorSteps.push(step);
        } else {
            okSteps.push(step);
        }
    });

    // draw rects
    ctx.beginPath();
    ctx.fillStyle = colors.node;
    okSteps.forEach((step) => {
        const rect = stateStore.stepPosition[step.id];
        ctx.rect(step.position!.left, step.position!.top, rect.width, rect.height);
    });
    ctx.fill();

    ctx.beginPath();
    ctx.fillStyle = colors.error;
    errorSteps.forEach((step) => {
        const rect = stateStore.stepPosition[step.id];
        ctx.rect(step.position!.left, step.position!.top, rect.width, rect.height);
    });
    ctx.fill();

    if (selectedStep) {
        const edge = 2 / scale;

        ctx.beginPath();
        ctx.strokeStyle = colors.selectedOutline;
        ctx.lineWidth = edge;
        const rect = stateStore.stepPosition[selectedStep.id];
        ctx.rect(
            selectedStep.position!.left - edge * 2,
            selectedStep.position!.top - edge * 2,
            rect.width + edge * 4,
            rect.height + edge * 4
        );
        ctx.stroke();
    }

    // draw view
    ctx.beginPath();
    ctx.strokeStyle = colors.viewOutline;
    ctx.fillStyle = colors.view;
    ctx.lineWidth = 1 / scale;
    ctx.rect(
        -props.viewportPan.x / props.viewportScale,
        -props.viewportPan.y / props.viewportScale,
        unref(props.viewportBounds.width) / props.viewportScale,
        unref(props.viewportBounds.height) / props.viewportScale
    );
    ctx.fill();
    ctx.stroke();
}
</script>

<template>
    <div ref="minimap" class="workflow-overview">
        <canvas ref="canvas" class="workflow-overview-body" width="300" height="300" />
    </div>
</template>

<style lang="scss" scoped>
@import "theme/blue.scss";

.workflow-overview-body {
    --node-color: #{$brand-primary};
    --error-color: #{$brand-warning};
    --selected-outline-color: #{$brand-info};
    --view-color: #{fade-out($brand-dark, 0.8)};
    --view-outline-color: #{$brand-info};
}
</style>
