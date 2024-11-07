import ELK, { type ElkExtendedEdge, type ElkNode } from "elkjs/lib/elk.bundled";

import { useConnectionStore } from "@/stores/workflowConnectionStore";
import { useWorkflowStateStore } from "@/stores/workflowEditorStateStore";
import { useWorkflowEditorToolbarStore } from "@/stores/workflowEditorToolbarStore";
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

export async function autoLayout(id: string, steps: { [index: string]: Step }) {
    const connectionStore = useConnectionStore(id);
    const stateStore = useWorkflowStateStore(id);
    const toolbarStore = useWorkflowEditorToolbarStore(id);

    const snappingDistance = Math.max(toolbarStore.snapActive ? toolbarStore.snapDistance : 0, 10);
    const horizontalDistance = Math.max(snappingDistance * 2, 100);
    const verticalDistance = Math.max(snappingDistance, 50);

    const roundUpToSnappingDistance = (value: number) => {
        const floatErrorTolerance = 0.0001;
        return Math.ceil(value / snappingDistance - floatErrorTolerance) * snappingDistance;
    };

    // Convert this to ELK compat.
    const newGraph: ElkNode = {
        id: "",
        layoutOptions: {
            "elk.algorithm": "layered",
            "elk.padding": elkSpacing(0, 0),
            "elk.spacing.nodeNode": `${verticalDistance}`,
            "elk.layered.spacing.baseValue": `${horizontalDistance}`,
            "crossingMinimization.semiInteractive": "true",
            "elk.layered.nodePlacement.strategy": "NETWORK_SIMPLEX",
            "elk.hierarchyHandling": "INCLUDE_CHILDREN",
            "elk.alignment": "TOP",
        },
        children: [],
        edges: [],
    };

    newGraph.children = Object.entries(steps).map(([stepId, step]) => {
        const inputs = Object.values(step.inputs).map((input) => {
            return {
                id: `${stepId}/in/${input.name}`,
                properties: {
                    "port.side": "WEST",
                    "port.index": step.id,
                },
            };
        });

        const outputs = Object.values(step.outputs).map((output) => {
            return {
                id: `${stepId}/out/${output.name}`,
                properties: {
                    "port.side": "EAST",
                    "port.index": step.id,
                },
            };
        });

        const position = stateStore.stepPosition[step.id];
        assertDefined(position, `No StepPosition with step id ${step.id} found in workflowStateStore`);

        return {
            id: stepId,
            height: roundUpToSnappingDistance(position.height),
            width: roundUpToSnappingDistance(position.width),
            ports: inputs.concat(outputs),
        };
    });

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
        // Reapply positions to galaxy graph from our relayed out graph.
        const positions = elkNode.children?.map((q) => ({
            id: q.id,
            x: roundToSnappingDistance(q.x as number),
            y: roundToSnappingDistance(q.y as number),
        }));
        return positions;
    } catch (error) {
        console.error(error);
    }
}
