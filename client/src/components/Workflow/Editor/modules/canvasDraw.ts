import { curveCatmullRom, line } from "d3";

import * as commentColours from "@/components/Workflow/Editor/Comments/colours";
import type {
    FrameWorkflowComment,
    FreehandWorkflowComment,
    MarkdownWorkflowComment,
    TextWorkflowComment,
} from "@/stores/workflowEditorCommentStore";
import type { useWorkflowStateStore } from "@/stores/workflowEditorStateStore";
import type { Step } from "@/stores/workflowStepStore";

export function drawBoxComments(
    ctx: CanvasRenderingContext2D,
    comments: FrameWorkflowComment[] | TextWorkflowComment[] | MarkdownWorkflowComment[],
    lineWidth: number,
    defaultColour: string,
    colourFill = false
) {
    ctx.lineWidth = lineWidth;

    if (colourFill) {
        comments.forEach((comment) => {
            ctx.beginPath();

            if (comment.colour !== "none") {
                ctx.fillStyle = commentColours.brighterColours[comment.colour];
                ctx.strokeStyle = commentColours.colours[comment.colour];
            } else {
                ctx.fillStyle = "rgba(0, 0, 0, 0)";
                ctx.strokeStyle = defaultColour;
            }

            ctx.rect(comment.position[0], comment.position[1], comment.size[0], comment.size[1]);
            ctx.fill();
            ctx.stroke();
        });
    } else {
        comments.forEach((comment) => {
            ctx.beginPath();

            if (comment.colour !== "none") {
                ctx.strokeStyle = commentColours.colours[comment.colour];
            } else {
                ctx.strokeStyle = defaultColour;
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
    colour: string,
    stateStore: ReturnType<typeof useWorkflowStateStore>
) {
    ctx.beginPath();
    ctx.fillStyle = colour;
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
    defaultColour: string
) {
    const catmullRom = line().curve(curveCatmullRom).context(ctx);

    comments.forEach((comment) => {
        if (comment.colour === "none") {
            ctx.strokeStyle = defaultColour;
        } else {
            ctx.strokeStyle = commentColours.colours[comment.colour];
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
