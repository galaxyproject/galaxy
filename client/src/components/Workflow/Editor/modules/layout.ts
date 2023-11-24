import ELK from "elkjs/lib/elk.bundled.js";
import { useWorkflowStateStore } from "@/stores/workflowEditorStateStore";
import type { Step } from "@/stores/workflowStepStore";
import { useConnectionStore } from "@/stores/workflowConnectionStore";
import { assertDefined } from "@/utils/assertions";

const elk = new ELK();

interface GraphChild {
    id: string;
    height: number;
    width: number;
    ports: {
        id: string;
        properties: {
            "port.side": string;
            "port.index": number;
        };
    }[];
}

interface GraphEdge {
    id: string;
    sources: string[];
    targets: string[];
}

interface NewGraph {
    id: string;
    layoutOptions: { [index: string]: string };
    children: GraphChild[];
    edges: GraphEdge[];
}

export async function autoLayout(steps: { [index: string]: Step }) {
    const stateStore = useWorkflowStateStore();
    const connectionStore = useConnectionStore();

    // Convert this to ELK compat.
    const newGraph: NewGraph = {
        id: "",
        layoutOptions: {
            "elk.algorithm": "layered",
            "crossingMinimization.semiInteractive": "true",
            "nodePlacement.strategy": "NETWORK_SIMPLEX",
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
            height: position.height + 20,
            width: position.width + 60,
            ports: inputs.concat(outputs),
        };
    });

    newGraph.edges = connectionStore.connections.map((connection) => {
        const edge: GraphEdge = {
            id: `e_${connection.input.stepId}_${connection.output.stepId}`,
            sources: [`${connection.output.stepId}/out/${connection.output.name}`],
            targets: [`${connection.input.stepId}/in/${connection.input.name}`],
        };
        return edge;
    });

    try {
        const elkNode = await elk.layout(newGraph);
        // Reapply positions to galaxy graph from our relayed out graph.
        const newSteps = elkNode.children?.map((q) => {
            const newStep = { ...steps[q.id], position: { top: q.y, left: q.x } };
            return newStep;
        });
        return newSteps;
    } catch (error) {
        console.error(error);
    }
}
