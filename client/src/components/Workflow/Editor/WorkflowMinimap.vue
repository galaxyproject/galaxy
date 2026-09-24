<script setup lang="ts">
import type { UseElementBoundingReturn } from "@vueuse/core";
import type { Ref } from "vue";
import { computed, nextTick, onMounted, ref, unref, watch } from "vue";

import { useAnimationFrame } from "@/composables/sensors/animationFrame";
import { useMinimapInteraction } from "@/composables/useMinimapInteraction";
import { useWorkflowStores } from "@/composables/workflowStores";
import type {
    FrameWorkflowComment,
    FreehandWorkflowComment,
    MarkdownWorkflowComment,
    TextWorkflowComment,
    WorkflowComment,
} from "@/stores/workflowEditorCommentStore";
import type { Step, Steps } from "@/stores/workflowStepStore";
import { AxisAlignedBoundingBox } from "@/utils/geometry";

import { useWorkflowBoundingBox } from "./composables/workflowBoundingBox";
import {
    drawBoxComments,
    drawFreehandComments,
    drawStepBorders,
    drawSteps,
    getStepColor,
    initStateColors,
} from "./modules/canvasDraw";

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

watch(
    () => props.viewportBoundingBox,
    () => (redraw = true),
    { deep: true },
);

const { getWorkflowBoundingBox } = useWorkflowBoundingBox();

let aabbChanged = false;

// Workflow-specific: compute padded, squared content bounds
const workflowContentBounds = ref(new AxisAlignedBoundingBox());

function recalculateAABB() {
    const aabb = getWorkflowBoundingBox();
    aabb.squareCenter();
    aabb.expand(120);
    workflowContentBounds.value = aabb;
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
    { deep: true },
);

// these settings are controlled via css, so they can be defined in one common place
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

onMounted(async () => {
    const element = canvas.value!;
    const style = getComputedStyle(element);

    colors.node = style.getPropertyValue("--node-color");
    colors.error = style.getPropertyValue("--error-color");
    colors.selectedOutline = style.getPropertyValue("--selected-outline-color");
    colors.view = style.getPropertyValue("--view-color");
    colors.viewOutline = style.getPropertyValue("--view-outline-color");

    initStateColors(style);

    size.default = parseInt(style.getPropertyValue("--workflow-overview-size"));
    size.min = parseInt(style.getPropertyValue("--workflow-overview-min-size"));
    size.max = parseInt(style.getPropertyValue("--workflow-overview-max-size"));
    size.padding = parseInt(style.getPropertyValue("--workflow-overview-padding"));
    size.border = parseInt(style.getPropertyValue("--workflow-overview-border"));

    await nextTick();

    recalculateAABB();
    redraw = true;
});

// ── Shared interaction ──

const minimap: Ref<HTMLElement | null> = ref(null);

const viewportBoundsRef = computed(() => props.viewportBoundingBox);
const parentRight = computed(() => unref(props.viewportBounds.right));
const parentBottom = computed(() => unref(props.viewportBounds.bottom));

const { getCanvasTransform, recomputeTransform, minimapSize } = useMinimapInteraction({
    canvasRef: canvas,
    containerRef: minimap,
    parentRight,
    parentBottom,
    contentBounds: workflowContentBounds,
    viewportBounds: viewportBoundsRef,
    panBy: (delta) => {
        if (Object.values(props.steps).length > 0) {
            emit("panBy", delta);
        }
    },
    moveTo: (pos) => {
        if (Object.values(props.steps).length > 0) {
            emit("moveTo", pos);
        }
    },
    storageKey: "overview-size",
    minSize: size.min,
    maxSize: size.max,
    defaultSize: size.default,
});

// for performance reasons, only draw and calculate on animation frames.
useAnimationFrame(() => {
    if (aabbChanged) {
        recalculateAABB();
        recomputeTransform();
        aabbChanged = false;
    }

    if (redraw && canvas.value) {
        renderMinimap();
        redraw = false;
    }
});

/** Renders the entire minimap to the canvas */
function renderMinimap() {
    const canvasTransform = getCanvasTransform();
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

    // group steps by their display color
    const allSteps = Object.values(props.steps);
    const stepsByColor = new Map<string, Step[]>();
    let selectedStep: Step | undefined;

    allSteps.forEach((step) => {
        if (stateStore.activeNodeId === step.id) {
            selectedStep = step;
        }
        const color = getStepColor(step, colors.node, colors.error);
        if (!stepsByColor.has(color)) {
            stepsByColor.set(color, []);
        }
        stepsByColor.get(color)?.push(step);
    });

    // draw rects
    drawBoxComments(ctx, frameComments, 2 / canvasTransform.scaleX, colors.node, true);
    ctx.fillStyle = "white";
    drawBoxComments(ctx, markdownComments, 2 / canvasTransform.scaleX, colors.node);
    ctx.fillStyle = "rgba(0, 0, 0, 0)";
    drawBoxComments(ctx, textComments, 1 / canvasTransform.scaleX, colors.node);
    stepsByColor.forEach((stepsForColor, color) => {
        drawSteps(ctx, stepsForColor, color, stateStore);
    });
    drawStepBorders(ctx, allSteps, colors.node, stateStore);

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
                rect.height + edge * 2,
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
        props.viewportBoundingBox.height,
    );
    ctx.fill();
    ctx.stroke();
}
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
@import "bootstrap/scss/_functions.scss";
@import "@/style/scss/theme/blue.scss";

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
    background: $workflow-overview-bg no-repeat url("@/assets/images/resizable.png");
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
