import ELK, { type ElkExtendedEdge, type ElkNode } from "elkjs/lib/elk.bundled";

import { useConnectionStore } from "@/stores/workflowConnectionStore";
import type { FreehandWorkflowComment, WorkflowComment } from "@/stores/workflowEditorCommentStore";
import { useWorkflowStateStore } from "@/stores/workflowEditorStateStore";
import { type Step } from "@/stores/workflowStepStore";
import { assertDefined } from "@/utils/assertions";
import { match } from "@/utils/utils";

import { AxisAlignedBoundingBox, type Rectangle, rectDistance } from "./geometry";

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

    const childLayoutOptions = {
        "elk.layered.spacing.nodeNodeBetweenLayers": `${horizontalDistance / 2}`,
        "elk.portConstraints": "FIXED_POS",
    };

    // Convert this to ELK compat.
    const newGraph: ElkNode = {
        id: "",
        layoutOptions: {
            "elk.padding": elkSpacing(0, 0),
            "elk.hierarchyHandling": "INCLUDE_CHILDREN",
            "elk.layered.spacing.baseValue": `${horizontalDistance}`,
            "elk.algorithm": "layered",
            "elk.layered.nodePlacement.strategy": "NETWORK_SIMPLEX",
            "elk.spacing.nodeNode": `${verticalDistance}`,
        },
        children: [],
        edges: [],
    };

    const freehandComments: FreehandWorkflowComment[] = [];
    const otherComments: WorkflowComment[] = [];

    comments.forEach((comment) => {
        if (comment.type === "freehand") {
            freehandComments.push(comment);
        } else {
            otherComments.push(comment);
        }
    });

    const stepsWithRect = Object.entries(steps).map(([stepId, step]) => {
        const position = stateStore.stepPosition[step.id];
        assertDefined(position, `No StepPosition with step id ${step.id} found in workflowStateStore`);

        return {
            id: stepId,
            step,
            rect: {
                x: step.position?.left ?? 0,
                y: step.position?.top ?? 0,
                width: position.width,
                height: position.height,
            },
        };
    });

    const collapsedFreehandComments = collapseFreehandComments(freehandComments);
    populateClosestSteps(collapsedFreehandComments, stepsWithRect);

    newGraph.children = graphToElkGraph(
        steps,
        otherComments,
        stateStore,
        roundUpToSnappingDistance,
        childLayoutOptions
    );

    const dataEdges = connectionStore.connections.map((connection) => {
        const edge: ElkExtendedEdge = {
            id: `e_${connection.input.stepId}_${connection.output.stepId}`,
            sources: [`${connection.output.stepId}/out/${connection.output.name}`],
            targets: [`${connection.input.stepId}/in/${connection.input.name}`],
        };
        return edge;
    });

    const commentEdges = getCommentEdges(otherComments, stepsWithRect);

    newGraph.edges = [...dataEdges, ...commentEdges];

    const roundToSnappingDistance = (value: number) => Math.round(value / snappingDistance) * snappingDistance;

    try {
        const elkNode = await elk.layout(newGraph);
        const positions = graphToPositions(elkNode.children, roundToSnappingDistance);

        const freehandPositions = resolveDeltaPositions(collapsedFreehandComments, positions.steps);
        positions.comments = positions.comments.concat(freehandPositions);

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
                const childComment = flatHierarchicalComments.get(id);

                if (childComment) {
                    childComment.root = false;
                    c.children.push(childComment);
                }
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
    let prefixObjectsCount = 0;
    const inputs = [];
    if (step.when) {
        inputs.push({
            id: `${step.id}/in/when`,
            properties: {
                "port.side": "WEST",
                "port.index": "0",
            },
            x: 0,
            y: 0,
        });
        prefixObjectsCount += 1;
    }
    Object.values(step.inputs).forEach((input, index) => {
        inputs.push({
            id: `${step.id}/in/${input.name}`,
            properties: {
                "port.side": "WEST",
                "port.index": `${index + prefixObjectsCount}`,
            },
            x: 0,
            y: (index + prefixObjectsCount) * 20,
        });
    });

    const position = stateStore.stepPosition[step.id];
    assertDefined(position, `No StepPosition with step id ${step.id} found in workflowStateStore`);

    const outputs = Object.values(step.outputs).map((output, index) => {
        return {
            id: `${step.id}/out/${output.name}`,
            properties: {
                "port.side": "EAST",
                "port.index": `${index}`,
            },
            x: position.width,
            y: index * 20,
        };
    });

    return {
        id: `${step.id}`,
        height: roundingFunction(position.height),
        width: roundingFunction(position.width),
        x: step.position?.left,
        y: step.position?.top,
        layoutOptions: {
            "elk.portConstraints": "FIXED_POS",
        },
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

function getCommentEdges(comments: WorkflowComment[], stepsWithRect: StepWithRect[]): ElkExtendedEdge[] {
    const edges: ElkExtendedEdge[] = [];

    comments.forEach((comment) => {
        if (comment.type === "freehand") {
            return;
        }

        let closestDistance = Infinity;
        let closestId: string | null = null;

        const commentRect = {
            x: comment.position[0],
            y: comment.position[1],
            width: comment.size[0],
            height: comment.size[1],
        };

        stepsWithRect.forEach((step) => {
            const distance = rectDistance(step.rect, commentRect);
            if (distance < closestDistance) {
                closestDistance = distance;
                closestId = step.id;
            }
        });

        if (closestId) {
            const edge: ElkExtendedEdge = {
                id: `comment_edge_${closestId}_${comment.id}`,
                sources: [closestId],
                targets: [`comment_${comment.id}`],
            };

            edges.push(edge);
        }
    });

    return edges;
}

interface CollapsedFreehandComment {
    aabb: AxisAlignedBoundingBox;
    comments: FreehandWorkflowComment[];
    closestStepId?: string;
    positionFrom?: { x: number; y: number };
}

/** groups freehand comments into distinct sets with any amount of overlap */
function collapseFreehandComments(comments: FreehandWorkflowComment[]): CollapsedFreehandComment[] {
    const commentsAsCollapsed: CollapsedFreehandComment[] = comments.map((c) => {
        const aabb = new AxisAlignedBoundingBox();
        aabb.fitRectangle({
            x: c.position[0],
            y: c.position[1],
            width: c.size[0],
            height: c.size[1],
        });

        return {
            aabb,
            comments: [c],
        };
    });

    const collapsedFreehandComments: Set<CollapsedFreehandComment> = new Set(commentsAsCollapsed);

    const compareAgainstOtherCollapsed = (a: CollapsedFreehandComment) => {
        const iterator = collapsedFreehandComments.values();

        for (const other of iterator) {
            if (a !== other && a.aabb.intersects(other.aabb)) {
                mergeCollapsedComments(a, other);
                break;
            }
        }
    };

    const mergeCollapsedComments = (a: CollapsedFreehandComment, b: CollapsedFreehandComment) => {
        const aabb = new AxisAlignedBoundingBox();
        aabb.fitRectangle(a.aabb);
        aabb.fitRectangle(b.aabb);

        collapsedFreehandComments.delete(a);
        collapsedFreehandComments.delete(b);

        const merged = {
            aabb: aabb,
            comments: [...a.comments, ...b.comments],
        };

        collapsedFreehandComments.add(merged);
        compareAgainstOtherCollapsed(merged);
    };

    const iterator = collapsedFreehandComments.values();

    for (const comment of iterator) {
        compareAgainstOtherCollapsed(comment);
    }

    return [...collapsedFreehandComments.values()];
}

interface StepWithRect {
    id: string;
    step: Step;
    rect: Rectangle;
}

/** find out which step is the closest to each comment, save it's id and position */
function populateClosestSteps(collapsedFreehandComments: CollapsedFreehandComment[], stepsWithRect: StepWithRect[]) {
    collapsedFreehandComments.forEach((comment) => {
        let closestDistance = Infinity;

        stepsWithRect.forEach((s) => {
            const distance = rectDistance(comment.aabb, s.rect);
            if (distance < closestDistance) {
                closestDistance = distance;
                comment.closestStepId = s.id;
                comment.positionFrom = {
                    x: s.rect.x,
                    y: s.rect.y,
                };
            }
        });
    });
}

/** resolve by how much to move the freehand comments */
function resolveDeltaPositions(
    collapsedFreehandComments: CollapsedFreehandComment[],
    stepPositions: Positions["steps"]
): Positions["comments"] {
    const positions: Positions["comments"] = [];
    const stepPositionMap = new Map(stepPositions.map((p) => [p.id, p]));

    collapsedFreehandComments.forEach((collapsed) => {
        if (!collapsed.closestStepId) {
            return;
        }

        const newPosition = stepPositionMap.get(collapsed.closestStepId);

        if (newPosition) {
            const delta = {
                x: newPosition.x - (collapsed.positionFrom?.x ?? 0),
                y: newPosition.y - (collapsed.positionFrom?.y ?? 0),
            };

            collapsed.comments.forEach((comment) => {
                positions.push({
                    id: `${comment.id}`,
                    x: comment.position[0] + delta.x,
                    y: comment.position[1] + delta.y,
                    w: comment.size[0],
                    h: comment.size[1],
                });
            });
        }
    });

    return positions;
}
