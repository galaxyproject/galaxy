import { curveCatmullRom, line } from "d3";

import * as commentColors from "@/components/Workflow/Editor/Comments/colors";
import {
    type FrameWorkflowComment,
    type FreehandWorkflowComment,
    type MarkdownWorkflowComment,
    type TextWorkflowComment,
} from "@/stores/workflowEditorCommentStore";
import { type useWorkflowStateStore } from "@/stores/workflowEditorStateStore";
import { type Step } from "@/stores/workflowStepStore";

export function drawBoxComments(
    ctx: CanvasRenderingContext2D,
    comments: FrameWorkflowComment[] | TextWorkflowComment[] | MarkdownWorkflowComment[],
    lineWidth: number,
    defaultColor: string,
    colorFill = false
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
    stateStore: ReturnType<typeof useWorkflowStateStore>
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

export function drawFreehandComments(
    ctx: CanvasRenderingContext2D,
    comments: FreehandWorkflowComment[],
    defaultColor: string
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
            (vec) => [vec[0] + comment.position[0], vec[1] + comment.position[1]] as [number, number]
        );

        ctx.beginPath();
        catmullRom(line);
        ctx.stroke();
        ctx.closePath();
    });
}
