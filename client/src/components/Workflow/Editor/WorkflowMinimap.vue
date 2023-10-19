<script setup lang="ts">
import { useDraggable, type UseElementBoundingReturn } from "@vueuse/core";
import type { Ref } from "vue";
import { computed, onMounted, ref, unref, watch } from "vue";

import { useAnimationFrame } from "@/composables/sensors/animationFrame";
import { useAnimationFrameThrottle } from "@/composables/throttle";
import { useWorkflowStores } from "@/composables/workflowStores";
import type {
    FrameWorkflowComment,
    FreehandWorkflowComment,
    MarkdownWorkflowComment,
    TextWorkflowComment,
    WorkflowComment,
} from "@/stores/workflowEditorCommentStore";
import type { Step, Steps } from "@/stores/workflowStepStore";

import { drawBoxComments, drawFreehandComments, drawSteps } from "./modules/canvasDraw";
import { AxisAlignedBoundingBox, Transform } from "./modules/geometry";

const props = defineProps<{
    steps: Steps;
    comments: WorkflowComment[];
    viewportBounds: UseElementBoundingReturn;
    viewportBoundingBox: AxisAlignedBoundingBox;
}>();

const emit = defineEmits<{
    (e: "panBy", offset: { x: number; y: number }): void;
    (e: "moveTo", position: { x: number; y: number }): void;
}>();

const { stateStore, commentStore, toolbarStore } = useWorkflowStores();
const { isJustCreated } = commentStore;

/** reference to the main canvas element */
const canvas: Ref<HTMLCanvasElement | null> = ref(null);
let redraw = false;

// it is important these throttles are defined before useAnimationFrame,
// so that they are executed first in the frame loop
const { throttle: dragThrottle } = useAnimationFrameThrottle();

watch(
    () => props.viewportBoundingBox,
    () => (redraw = true),
    { deep: true }
);

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

    props.comments.forEach((comment) => {
        aabb.fitRectangle({
            x: comment.position[0],
            y: comment.position[1],
            width: comment.size[0],
            height: comment.size[1],
        });
    });

    aabb.squareCenter();
    aabb.expand(120);

    // transform canvas to show entire workflow bounding box
    if (canvas.value) {
        const scale = canvas.value.width / aabb.width;
        canvasTransform = new Transform().translate([-aabb.x * scale, -aabb.y * scale]).scale([scale, scale]);
    }
}

// redraw if any steps or comments change
watch(
    () => [props.steps, props.comments, toolbarStore.inputCatcherPressed],
    () => {
        if (!toolbarStore.inputCatcherPressed) {
            redraw = true;
            aabbChanged = true;
        }
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

    // sort comments by type
    const frameComments: FrameWorkflowComment[] = [];
    const markdownComments: MarkdownWorkflowComment[] = [];
    const textComments: TextWorkflowComment[] = [];
    const freehandComments: FreehandWorkflowComment[] = [];

    props.comments.forEach((comment) => {
        if (comment.type === "frame") {
            frameComments.push(comment);
        } else if (comment.type === "markdown") {
            markdownComments.push(comment);
        } else if (comment.type === "text") {
            textComments.push(comment);
        } else {
            if (!isJustCreated(comment.id)) {
                freehandComments.push(comment);
            }
        }
    });

    // sort steps by error state
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
    drawBoxComments(ctx, frameComments, 2 / canvasTransform.scaleX, colors.node, true);
    ctx.fillStyle = "white";
    drawBoxComments(ctx, markdownComments, 2 / canvasTransform.scaleX, colors.node);
    ctx.fillStyle = "rgba(0, 0, 0, 0)";
    drawBoxComments(ctx, textComments, 1 / canvasTransform.scaleX, colors.node);
    drawSteps(ctx, okSteps, colors.node, stateStore);
    drawSteps(ctx, errorSteps, colors.error, stateStore);

    drawFreehandComments(ctx, freehandComments, colors.node);

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
    ctx.rect(
        props.viewportBoundingBox.x,
        props.viewportBoundingBox.y,
        props.viewportBoundingBox.width,
        props.viewportBoundingBox.height
    );
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

        if (props.viewportBoundingBox.isPointInBounds({ x, y })) {
            dragViewport = true;
        }
    },
    onMove: (position, event) => {
        dragThrottle(() => {
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
        });
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

.workflow-overview {
    --workflow-overview-size: 150px;
    --workflow-overview-min-size: 50px;
    --workflow-overview-max-size: 300px;
    --workflow-overview-padding: 7px;
    --workflow-overview-border: 1px;

    border-top-left-radius: 0.3rem;
    cursor: nwse-resize;
    position: absolute;
    width: var(--workflow-overview-size);
    height: var(--workflow-overview-size);
    right: 0px;
    bottom: 0px;
    border-top: solid $border-color var(--workflow-overview-border);
    border-left: solid $border-color var(--workflow-overview-border);
    background: $workflow-overview-bg no-repeat url("assets/images/resizable.png");
    z-index: 20000;
    overflow: hidden;
    padding: var(--workflow-overview-padding) 0 0 var(--workflow-overview-padding);

    // account for padding and border
    max-width: calc(
        var(--workflow-overview-max-size) + var(--workflow-overview-padding) + var(--workflow-overview-border)
    );
    max-height: calc(
        var(--workflow-overview-max-size) + var(--workflow-overview-padding) + var(--workflow-overview-border)
    );
    min-width: calc(
        var(--workflow-overview-min-size) + var(--workflow-overview-padding) + var(--workflow-overview-border)
    );
    min-height: calc(
        var(--workflow-overview-min-size) + var(--workflow-overview-padding) + var(--workflow-overview-border)
    );

    .workflow-overview-body {
        cursor: pointer;
        position: relative;
        overflow: hidden;
        width: 100%;
        height: 100%;

        --node-color: #{$brand-primary};
        --error-color: #{$state-danger-bg};
        --selected-outline-color: #{$brand-primary};
        --view-color: #{fade-out($brand-dark, 0.8)};
        --view-outline-color: #{$brand-info};
    }
}
</style>
