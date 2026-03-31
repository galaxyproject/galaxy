import { curveCatmullRom, line } from "d3";

import * as commentColors from "@/components/Workflow/Editor/Comments/colors";
import type { GraphStep } from "@/composables/useInvocationGraph";
import type {
    FrameWorkflowComment,
    FreehandWorkflowComment,
    MarkdownWorkflowComment,
    TextWorkflowComment,
} from "@/stores/workflowEditorCommentStore";
import type { useWorkflowStateStore } from "@/stores/workflowEditorStateStore";
import type { Step } from "@/stores/workflowStepStore";

const stateNames = [
    "new",
    "waiting",
    "queued",
    "running",
    "ok",
    "error",
    "deleted",
    "setting_metadata",
    "paused",
    "skipped",
    "upload",
    "hidden",
] as const;

const stateColors: Record<string, string> = {};

/** Initialize the state colors for minimap nodes from CSS variables.
 * This should be called once when the minimap is mounted. */
export function initStateColors(style: CSSStyleDeclaration) {
    for (const state of stateNames) {
        const cssKey = state.replace("_", "-");
        stateColors[state] = style.getPropertyValue(`--state-color-${cssKey}`);
    }
}

/** Get the color for a minimap step based on its state (invocation view) and errors. */
export function getStepColor(step: Step, nodeColor: string, errorColor: string): string {
    const graphStep = step as GraphStep;
    if (graphStep.headerClass) {
        for (const [key, active] of Object.entries(graphStep.headerClass)) {
            if (active && key.startsWith("header-")) {
                const color = stateColors[key.slice(7)];
                if (color) {
                    return color;
                }
            }
        }
    }
    return step.errors ? errorColor : nodeColor;
}

export function drawBoxComments(
    ctx: CanvasRenderingContext2D,
    comments: FrameWorkflowComment[] | TextWorkflowComment[] | MarkdownWorkflowComment[],
    lineWidth: number,
    defaultColor: string,
    colorFill = false,
) {
    ctx.lineWidth = lineWidth;

    if (colorFill) {
        comments.forEach((comment) => {
            ctx.beginPath();

            if (comment.color !== "none") {
                ctx.fillStyle = commentColors.brighterColors[comment.color];
                ctx.strokeStyle = commentColors.colors[comment.color];
            } else {
                ctx.fillStyle = "rgba(0, 0, 0, 0)";
                ctx.strokeStyle = defaultColor;
            }

            ctx.rect(comment.position[0], comment.position[1], comment.size[0], comment.size[1]);
            ctx.fill();
            ctx.stroke();
        });
    } else {
        comments.forEach((comment) => {
            ctx.beginPath();

            if (comment.color !== "none") {
                ctx.strokeStyle = commentColors.colors[comment.color];
            } else {
                ctx.strokeStyle = defaultColor;
            }

            ctx.rect(comment.position[0], comment.position[1], comment.size[0], comment.size[1]);
            ctx.fill();
            ctx.stroke();
        });
    }
}

export function drawSteps(
    ctx: CanvasRenderingContext2D,
    steps: Step[],
    color: string,
    stateStore: ReturnType<typeof useWorkflowStateStore>,
) {
    ctx.beginPath();
    ctx.fillStyle = color;
    steps.forEach((step) => {
        const rect = stateStore.stepPosition[step.id];

        if (rect) {
            ctx.rect(step.position!.left, step.position!.top, rect.width, rect.height);
        }
    });
    ctx.fill();
}

/** Draw borders around minimap steps. This is needed to make step boundaries visible when
 * step colors are very light (in the invocation view where steps can have states). */
export function drawStepBorders(
    ctx: CanvasRenderingContext2D,
    steps: Step[],
    borderColor: string,
    stateStore: ReturnType<typeof useWorkflowStateStore>,
) {
    ctx.beginPath();
    ctx.strokeStyle = borderColor;
    ctx.lineWidth = 1;
    steps.forEach((step) => {
        const rect = stateStore.stepPosition[step.id];

        if (rect && step.position) {
            ctx.rect(step.position.left, step.position.top, rect.width, rect.height);
        }
    });
    ctx.stroke();
}

export function drawFreehandComments(
    ctx: CanvasRenderingContext2D,
    comments: FreehandWorkflowComment[],
    defaultColor: string,
) {
    const catmullRom = line().curve(curveCatmullRom).context(ctx);

    comments.forEach((comment) => {
        if (comment.color === "none") {
            ctx.strokeStyle = defaultColor;
        } else {
            ctx.strokeStyle = commentColors.colors[comment.color];
        }

        ctx.lineWidth = comment.data.thickness;

        const line = comment.data.line.map(
            (vec) => [vec[0] + comment.position[0], vec[1] + comment.position[1]] as [number, number],
        );

        ctx.beginPath();
        catmullRom(line);
        ctx.stroke();
        ctx.closePath();
    });
}
