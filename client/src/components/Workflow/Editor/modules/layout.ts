import ELK, { type ElkExtendedEdge, type ElkNode } from "elkjs/lib/elk.bundled";

import { useConnectionStore } from "@/stores/workflowConnectionStore";
import type { WorkflowComment } from "@/stores/workflowEditorCommentStore";
import { useWorkflowStateStore } from "@/stores/workflowEditorStateStore";
import { type Step } from "@/stores/workflowStepStore";
import { assertDefined } from "@/utils/assertions";
import { match } from "@/utils/utils";

const elk = new ELK();

interface OptionObject {
    [key: string]: OptionValue | OptionObject;
}
type OptionValue = number | string | boolean;

export function elkOptionObject(object: OptionObject): string {
    const entries = Object.entries(object);
    const stringifiedEntries = entries.map(([key, value]) => {
        const type = typeof value as "number" | "string" | "boolean" | "object";

        const valueAsString = match(type, {
            number: () => `${value}`,
            string: () => `"${value}"`,
            boolean: () => `${value}`,
            object: () => elkOptionObject(value as OptionObject),
        });

        return `${key}=${valueAsString}`;
    });

    return `[${stringifiedEntries.join(", ")}]`;
}

export function elkSpacing(left = 0, top = 0, right = 0, bottom = 0) {
    return elkOptionObject({
        left,
        top,
        right,
        bottom,
    });
}

export async function autoLayout(id: string, steps: { [index: string]: Step }, comments: WorkflowComment[]) {
    const connectionStore = useConnectionStore(id);
    const stateStore = useWorkflowStateStore(id);

    // making this follow the user set snapping distance get's messy fast, so it's hardcoded for simplicity
    const snappingDistance = 10;
    const horizontalDistance = Math.max(snappingDistance * 2, 100);
    const verticalDistance = Math.max(snappingDistance, 50);

    const roundUpToSnappingDistance = (value: number) => {
        const floatErrorTolerance = 0.0001;
        return Math.ceil(value / snappingDistance - floatErrorTolerance) * snappingDistance;
    };

    const baseLayoutOptions = {
        "elk.layered.spacing.nodeNodeBetweenLayers": `${horizontalDistance / 2}`,
    };

    // Convert this to ELK compat.
    const newGraph: ElkNode = {
        id: "",
        layoutOptions: {
            ...baseLayoutOptions,
            "elk.padding": elkSpacing(0, 0),
            "elk.hierarchyHandling": "INCLUDE_CHILDREN",
            "elk.layered.spacing.baseValue": `${horizontalDistance}`,
            "elk.algorithm": "layered",
            "elk.layered.nodePlacement.strategy": "NETWORK_SIMPLEX",
            "elk.spacing.nodeNode": `${verticalDistance}`,
            "crossingMinimization.semiInteractive": "true",
            "elk.alignment": "TOP",
        },
        children: [],
        edges: [],
    };

    newGraph.children = graphToElkGraph(steps, comments, stateStore, roundUpToSnappingDistance, baseLayoutOptions);

    newGraph.edges = connectionStore.connections.map((connection) => {
        const edge: ElkExtendedEdge = {
            id: `e_${connection.input.stepId}_${connection.output.stepId}`,
            sources: [`${connection.output.stepId}/out/${connection.output.name}`],
            targets: [`${connection.input.stepId}/in/${connection.input.name}`],
        };
        return edge;
    });

    const roundToSnappingDistance = (value: number) => Math.round(value / snappingDistance) * snappingDistance;

    try {
        const elkNode = await elk.layout(newGraph);
        const positions = graphToPositions(elkNode.children, roundToSnappingDistance);
        console.log(positions);
        return positions;
    } catch (error) {
        console.error(error);
    }
}

interface HierarchicalComment {
    comment: WorkflowComment;
    root: boolean;
    children: (HierarchicalComment | Step)[];
}

function graphToElkGraph(
    steps: Record<number, Step>,
    comments: WorkflowComment[],
    stateStore: ReturnType<typeof useWorkflowStateStore>,
    roundingFunction: (value: number) => number,
    layoutOptions: Record<string, string>
): ElkNode[] {
    const flatHierarchicalComments: Map<number, HierarchicalComment> = new Map(
        comments.map((comment) => [comment.id, { comment, root: true, children: [] }])
    );

    const rootSteps = new Map(Object.entries(steps));

    flatHierarchicalComments.forEach((c) => {
        if (c.comment.child_comments) {
            c.comment.child_comments.forEach((id) => {
                const childComment = flatHierarchicalComments.get(id)!;
                childComment.root = false;
                c.children.push(childComment);
            });
        }

        if (c.comment.child_steps) {
            c.comment.child_steps.forEach((id) => {
                const idAsString = `${id}`;
                const childStep = rootSteps.get(idAsString)!;
                rootSteps.delete(idAsString);
                c.children.push(childStep);
            });
        }
    });

    const rootHierarchicalComments: HierarchicalComment[] = [...flatHierarchicalComments.values()].filter(
        (c) => c.root
    );

    const elkRootSteps = [...rootSteps.values()].map((step) => {
        return stepToElkStep(step, stateStore, roundingFunction);
    });

    const elkRootComments = rootHierarchicalComments.map((c) =>
        commentToElkStep(c, stateStore, roundingFunction, layoutOptions)
    );

    return [...elkRootSteps, ...elkRootComments];
}

function stepToElkStep(
    step: Step,
    stateStore: ReturnType<typeof useWorkflowStateStore>,
    roundingFunction: (value: number) => number
): ElkNode {
    const inputs = Object.values(step.inputs).map((input) => {
        return {
            id: `${step.id}/in/${input.name}`,
            properties: {
                "port.side": "WEST",
                "port.index": step.id,
            },
        };
    });

    const outputs = Object.values(step.outputs).map((output) => {
        return {
            id: `${step.id}/out/${output.name}`,
            properties: {
                "port.side": "EAST",
                "port.index": step.id,
            },
        };
    });

    const position = stateStore.stepPosition[step.id];
    assertDefined(position, `No StepPosition with step id ${step.id} found in workflowStateStore`);

    return {
        id: `${step.id}`,
        height: roundingFunction(position.height),
        width: roundingFunction(position.width),
        ports: inputs.concat(outputs),
    };
}

function commentToElkStep(
    hierarchicalComment: HierarchicalComment,
    stateStore: ReturnType<typeof useWorkflowStateStore>,
    roundingFunction: (value: number) => number,
    layoutOptions: Record<string, string>
): ElkNode {
    const base: ElkNode = {
        id: `comment_${hierarchicalComment.comment.id}`,
        x: hierarchicalComment.comment.position[0],
        y: hierarchicalComment.comment.position[1],
        width: hierarchicalComment.comment.size[0],
        height: hierarchicalComment.comment.size[1],
        layoutOptions: {
            "elk.commentBox": hierarchicalComment.comment.type === "frame" ? "false" : "true",
            ...layoutOptions,
            "elk.padding": elkSpacing(20, 40, 20, 20),
        },
    };

    const children: ElkNode[] = hierarchicalComment.children?.map((c) => {
        if ("comment" in c) {
            return commentToElkStep(c, stateStore, roundingFunction, layoutOptions);
        } else {
            return stepToElkStep(c, stateStore, roundingFunction);
        }
    });

    return { ...base, children };
}

interface Positions {
    steps: { id: string; x: number; y: number }[];
    comments: { id: string; x: number; y: number; w: number; h: number }[];
}

function graphToPositions(
    graph: ElkNode[] | undefined,
    roundingFunction: (value: number) => number,
    parentPosition?: { x: number; y: number }
): Positions {
    const positions: Positions = {
        steps: [],
        comments: [],
    };

    if (!graph) {
        return positions;
    }

    const offset = parentPosition ?? { x: 0, y: 0 };

    graph.forEach((node) => {
        if (!node.id.startsWith("comment_")) {
            positions.steps.push({
                id: node.id,
                x: roundingFunction(node.x ?? 0) + offset.x,
                y: roundingFunction(node.y ?? 0) + offset.y,
            });
        } else {
            const id = node.id.slice("comment_".length);

            const position = {
                x: roundingFunction(node.x ?? 0) + offset.x,
                y: roundingFunction(node.y ?? 0) + offset.y,
            };

            positions.comments.push({
                id,
                ...position,
                w: node.width ?? 0,
                h: node.height ?? 0,
            });

            if (node.children) {
                const childPositions = graphToPositions(node.children, roundingFunction, position);

                positions.steps = positions.steps.concat(childPositions.steps);
                positions.comments = positions.comments.concat(childPositions.comments);
            }
        }
    });

    return positions;
}
