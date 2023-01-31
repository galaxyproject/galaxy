<script lang="ts" setup>
import { computed, onMounted, ref, unref, watch } from "vue";
import { useAnimationFrame } from "@/composables/sensors/animationFrame";
import { useWorkflowStateStore } from "@/stores/workflowEditorStateStore";
import { AxisAlignedBoundingBox, Transform } from "./modules/geomerty";
import { useDraggable, type UseElementBoundingReturn } from "@vueuse/core";

import type { Step, Steps } from "@/stores/workflowStepStore";
import type { PropType, Ref } from "vue";

const props = defineProps({
    steps: {
        type: Object as PropType<Steps>,
        required: true,
    },
    viewportBounds: {
        type: Object as PropType<UseElementBoundingReturn>,
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

const emit = defineEmits<{
    (e: "pan-by", offset: { x: number; y: number }): void;
    (e: "moveTo", position: { x: number; y: number }): void;
}>();

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

const size = {
    default: 150,
    min: 50,
    max: 300,
    padding: 5,
    border: 0,
};

onMounted(() => {
    // these settings are controlled via css, so they can be defined in one common place
    // this ensures future style changes wont break the minimap's behavior
    const element = canvas.value!;
    const style = getComputedStyle(element);

    colors.node = style.getPropertyValue("--node-color");
    colors.error = style.getPropertyValue("--error-color");
    colors.selectedOutline = style.getPropertyValue("--selected-outline-color");
    colors.view = style.getPropertyValue("--view-color");
    colors.viewOutline = style.getPropertyValue("--view-outline-color");

    size.default = parseInt(style.getPropertyValue("--workflow-overview-size"));
    size.min = parseInt(style.getPropertyValue("--workflow-overview-min-size"));
    size.max = parseInt(style.getPropertyValue("--workflow-overview-max-size"));
    size.padding = parseInt(style.getPropertyValue("--workflow-overview-padding"));
    size.border = parseInt(style.getPropertyValue("--workflow-overview-border"));

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

let canvasTransform = new Transform();

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
    aabb.expand(120);

    if (canvas.value) {
        const scale = canvas.value.width / aabb.width;
        canvasTransform = new Transform().translate([-aabb.x * scale, -aabb.y * scale]).scale([scale, scale]);
    }
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

    canvasTransform.applyToContext(ctx);

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
        const edge = 2 / canvasTransform.scaleX;

        ctx.beginPath();
        ctx.strokeStyle = colors.selectedOutline;
        ctx.lineWidth = edge;
        const rect = stateStore.stepPosition[selectedStep.id];
        ctx.rect(
            selectedStep.position!.left - edge,
            selectedStep.position!.top - edge,
            rect.width + edge * 2,
            rect.height + edge * 2
        );
        ctx.stroke();
    }

    // draw viewport
    ctx.beginPath();
    ctx.strokeStyle = colors.viewOutline;
    ctx.fillStyle = colors.view;
    ctx.lineWidth = 1 / canvasTransform.scaleX;
    ctx.rect(
        -props.viewportPan.x / props.viewportScale,
        -props.viewportPan.y / props.viewportScale,
        unref(props.viewportBounds.width) / props.viewportScale,
        unref(props.viewportBounds.height) / props.viewportScale
    );
    ctx.fill();
    ctx.stroke();
}

// resizing
const minimap: Ref<HTMLCanvasElement | null> = ref(null);
const { position: dragHandlePosition, isDragging: isHandleDragging } = useDraggable(minimap, {
    preventDefault: true,
    exact: true,
});
const minimapSize = ref(parseInt(localStorage.getItem("overview-size") || size.default.toString()));

watch(dragHandlePosition, () => {
    // resize
    minimapSize.value = Math.max(
        unref(props.viewportBounds.right) - dragHandlePosition.value.x,
        unref(props.viewportBounds.bottom) - dragHandlePosition.value.y
    );

    // clamp
    minimapSize.value = Math.min(Math.max(minimapSize.value, size.min), size.max);
});

watch(isHandleDragging, () => {
    if (!isHandleDragging.value) {
        localStorage.setItem("overview-size", minimapSize.value.toString());
    }
});

// repositioning
const scaleFactor = computed(() => size.max / minimapSize.value);
let dragViewport = false;

useDraggable(canvas, {
    onStart: (position, event) => {
        const bounds = new AxisAlignedBoundingBox();
        bounds.x = -props.viewportPan.x / props.viewportScale;
        bounds.y = -props.viewportPan.y / props.viewportScale;
        bounds.width = unref(props.viewportBounds.width) / props.viewportScale;
        bounds.height = unref(props.viewportBounds.height) / props.viewportScale;

        const [x, y] = canvasTransform
            .inverse()
            .scale([scaleFactor.value, scaleFactor.value])
            .apply([event.offsetX, event.offsetY]);

        if (bounds.isPointInBounds({ x, y })) {
            dragViewport = true;
        }
    },
    onMove: (position, event) => {
        if (!dragViewport || Object.values(props.steps).length === 0) {
            return;
        }

        const [x, y] = canvasTransform
            .resetTranslation()
            .inverse()
            .scale([scaleFactor.value, scaleFactor.value])
            .apply([-event.movementX, -event.movementY]);

        emit("pan-by", { x, y });
    },
    onEnd(position, event) {
        const [x, y] = canvasTransform
            .inverse()
            .scale([scaleFactor.value, scaleFactor.value])
            .apply([event.offsetX, event.offsetY]);

        if (!dragViewport && Object.values(props.steps).length > 0) {
            emit("moveTo", { x, y });
        }

        dragViewport = false;
    },
    exact: true,
});
</script>

<template>
    <div
        ref="minimap"
        class="workflow-overview"
        :style="{ '--workflow-overview-size': `${minimapSize + size.padding + size.border}px` }">
        <canvas ref="canvas" class="workflow-overview-body" :width="size.max" :height="size.max" />
    </div>
</template>

<style lang="scss" scoped>
@import "theme/blue.scss";

.workflow-overview-body {
    --node-color: #{$brand-primary};
    --error-color: #{$brand-warning};
    --selected-outline-color: #{$brand-primary};
    --view-color: #{fade-out($brand-dark, 0.8)};
    --view-outline-color: #{$brand-info};
}
</style>
