<script lang="ts" setup>
import { computed, onMounted, ref, unref, watch } from "vue";
import { useAnimationFrame } from "@/composables/sensors/animationFrame";
import { useWorkflowStateStore } from "@/stores/workflowEditorStateStore";
import { AxisAlignedBoundingBox, Transform } from "./modules/geometry";
import { useDraggable, type UseElementBoundingReturn } from "@vueuse/core";

import type { Step, Steps } from "@/stores/workflowStepStore";
import type { Ref } from "vue";

const props = defineProps<{
    steps: Steps;
    viewportBounds: UseElementBoundingReturn;
    viewportPan: { x: number; y: number };
    viewportScale: number;
}>();

const emit = defineEmits<{
    (e: "panBy", offset: { x: number; y: number }): void;
    (e: "moveTo", position: { x: number; y: number }): void;
}>();

const stateStore = useWorkflowStateStore();

/** bounding box following the viewport */
const viewportBounds = computed(() => {
    const bounds = new AxisAlignedBoundingBox();
    bounds.x = -props.viewportPan.x / props.viewportScale;
    bounds.y = -props.viewportPan.y / props.viewportScale;
    bounds.width = unref(props.viewportBounds.width) / props.viewportScale;
    bounds.height = unref(props.viewportBounds.height) / props.viewportScale;

    return bounds;
});

/** reference to the main canvas element */
const canvas: Ref<HTMLCanvasElement | null> = ref(null);
let redraw = false;

/** bounding box encompassing all nodes in the workflow */
const aabb = new AxisAlignedBoundingBox();
let aabbChanged = false;

/** transform mapping workflow coordinates to minimap coordinates */
let canvasTransform = new Transform();

function recalculateAABB() {
    aabb.reset();

    Object.values(props.steps).forEach((step) => {
        const rect = stateStore.stepPosition[step.id];

        if (rect) {
            aabb.fitRectangle({
                x: step.position!.left,
                y: step.position!.top,
                width: rect.width,
                height: rect.height,
            });
        }
    });

    aabb.squareCenter();
    aabb.expand(120);

    // transform canvas to show entire workflow bounding box
    if (canvas.value) {
        const scale = canvas.value.width / aabb.width;
        canvasTransform = new Transform().translate([-aabb.x * scale, -aabb.y * scale]).scale([scale, scale]);
    }
}

// redraw if any of these props change
watch(viewportBounds, () => (redraw = true));
watch(
    props.steps,
    () => {
        redraw = true;
        aabbChanged = true;
    },
    { deep: true }
);

// these settings are controlled via css, so they can be defined in one common place
// this ensures future style changes wont break the minimap's behavior
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

// for performance reasons, only draw and calculate on animation frames.
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

/** Renders the entire minimap to the canvas */
function renderMinimap() {
    const ctx = canvas.value!.getContext("2d") as CanvasRenderingContext2D;
    ctx.resetTransform();
    ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);

    // apply global to local transform
    canvasTransform.applyToContext(ctx);

    const allSteps = Object.values(props.steps);
    const okSteps: Step[] = [];
    const errorSteps: Step[] = [];
    let selectedStep: Step | undefined;

    // sort steps into different arrays
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

        if (rect) {
            ctx.rect(step.position!.left, step.position!.top, rect.width, rect.height);
        }
    });
    ctx.fill();

    ctx.beginPath();
    ctx.fillStyle = colors.error;
    errorSteps.forEach((step) => {
        const rect = stateStore.stepPosition[step.id];

        if (rect) {
            ctx.rect(step.position!.left, step.position!.top, rect.width, rect.height);
        }
    });
    ctx.fill();

    // draw selected
    if (selectedStep) {
        const edge = 2 / canvasTransform.scaleX;

        ctx.beginPath();
        ctx.strokeStyle = colors.selectedOutline;
        ctx.lineWidth = edge;
        const rect = stateStore.stepPosition[selectedStep.id];

        if (rect) {
            ctx.rect(
                selectedStep.position!.left - edge,
                selectedStep.position!.top - edge,
                rect.width + edge * 2,
                rect.height + edge * 2
            );
        }

        ctx.stroke();
    }

    // draw viewport
    ctx.beginPath();
    ctx.strokeStyle = colors.viewOutline;
    ctx.fillStyle = colors.view;
    ctx.lineWidth = 1 / canvasTransform.scaleX;
    ctx.rect(viewportBounds.value.x, viewportBounds.value.y, viewportBounds.value.width, viewportBounds.value.height);
    ctx.fill();
    ctx.stroke();
}

// -- Resizing --
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

// -- Repositioning Viewport --

/** Scaling factor of the canvas element. Draw size in relation to actual size on screen */
const scaleFactor = computed(() => size.max / minimapSize.value);
let dragViewport = false;

useDraggable(canvas, {
    onStart: (position, event) => {
        // minimap coordinates to global coordinates
        const [x, y] = canvasTransform
            .inverse()
            .scale([scaleFactor.value, scaleFactor.value])
            .apply([event.offsetX, event.offsetY]);

        if (viewportBounds.value.isPointInBounds({ x, y })) {
            dragViewport = true;
        }
    },
    onMove: (position, event) => {
        if (!dragViewport || Object.values(props.steps).length === 0) {
            return;
        }

        // minimap coordinates to global coordinates, without translation
        const [x, y] = canvasTransform
            .resetTranslation()
            .inverse()
            .scale([scaleFactor.value, scaleFactor.value])
            .apply([-event.movementX, -event.movementY]);

        emit("panBy", { x, y });
    },
    onEnd(position, event) {
        // minimap coordinates to global coordinates
        const [x, y] = canvasTransform
            .inverse()
            .scale([scaleFactor.value, scaleFactor.value])
            .apply([event.offsetX, event.offsetY]);

        if (!dragViewport && Object.values(props.steps).length > 0) {
            emit("moveTo", { x, y });
        }

        dragViewport = false;
    },
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
@import "~bootstrap/scss/_functions.scss";
@import "theme/blue.scss";

.workflow-overview-body {
    --node-color: #{$brand-primary};
    --error-color: #{$state-danger-bg};
    --selected-outline-color: #{$brand-primary};
    --view-color: #{fade-out($brand-dark, 0.8)};
    --view-outline-color: #{$brand-info};
}
</style>
