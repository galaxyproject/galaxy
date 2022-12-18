import { setActivePinia, createPinia } from "pinia";

import { useWorkflowStepStore, type Step } from "@/stores/workflowStepStore";
import {
    InputCollectionTerminal,
    InputTerminal,
    InputParameterTerminal,
    OutputCollectionTerminal,
    OutputTerminal,
    OutputParameterTerminal,
} from "./terminals";
import * as _simpleSteps from "../test-data/simple_steps.json";
import * as advancedSteps from "../test-data/parameter_steps.json";
import { testDatatypesMapper } from "@/components/Datatypes/test_fixtures";
import { useConnectionStore } from "@/stores/workflowConnectionStore";

const simpleSteps = _simpleSteps as { [index: string]: Step };

describe("Input terminal", () => {
    let stepStore: ReturnType<typeof useWorkflowStepStore>;
    let connectionStore: ReturnType<typeof useConnectionStore>;
    let inputTerminals: InputTerminal[] = [];
    let outputTerminals: OutputTerminal[] = [];
    beforeEach(() => {
        setActivePinia(createPinia());
        stepStore = useWorkflowStepStore();
        connectionStore = useConnectionStore();
        inputTerminals = [];
        outputTerminals = [];
        Object.entries(simpleSteps).map(([key, step]) => {
            stepStore.addStep(step);
            step.inputs?.map((input) => {
                const inputTerminal = new InputTerminal({
                    datatypesMapper: testDatatypesMapper,
                    stepId: step.id,
                    name: input.name,
                    type: "input",
                    input: { ...input, datatypes: input.extensions },
                });
                inputTerminals.push(inputTerminal);
            });
            step.outputs?.map((output) => {
                const outputTerminal = new OutputTerminal({
                    name: output.name,
                    stepId: step.id,
                    datatypes: output.extensions,
                    optional: output.optional,
                    type: "output",
                });
                outputTerminals.push(outputTerminal);
            });
        });
    });

    it("has step", () => {
        expect(stepStore.getStep(1)).toEqual(simpleSteps["1"]);
    });
    it("infers correct state", () => {
        const firstInputTerminal = inputTerminals[0];
        expect(firstInputTerminal.connections.length).toBe(1);
        expect(firstInputTerminal.mapOver).toBe(null);
        expect(firstInputTerminal.isMappedOver()).toBe(false);
        expect(firstInputTerminal.hasConnectedMappedInputTerminals()).toBe(false);
        expect(firstInputTerminal.hasMappedOverInputTerminals()).toBe(false);
        expect(firstInputTerminal.hasConnectedOutputTerminals()).toBe(false);
        const canAccept = firstInputTerminal.canAccept(outputTerminals[0]);
        expect(canAccept.canAccept).toBe(false);
        expect(canAccept.reason).toBe(
            "Input already filled with another connection, delete it before connecting another output."
        );
        // bypasses _inputFilled check
        expect(firstInputTerminal.attachable(outputTerminals[1]).canAccept).toBe(true);
        expect(firstInputTerminal.connected()).toBe(true);
        expect(firstInputTerminal._collectionAttached()).toBe(false);
        expect(firstInputTerminal._producesAcceptableDatatype(outputTerminals[1]).canAccept).toBe(true);
    });
    it("can accept new connection", () => {
        const firstInputTerminal = inputTerminals[0];
        const connection = firstInputTerminal.connections[0];
        expect(firstInputTerminal.canAccept(outputTerminals[0]).canAccept).toBe(false);
        connectionStore.removeConnection(connection.id);
        expect(firstInputTerminal.canAccept(outputTerminals[0]).canAccept).toBe(true);
        connectionStore.addConnection(connection);
        expect(firstInputTerminal.canAccept(outputTerminals[0]).canAccept).toBe(false);
    });
});

function terminalFactory(step: Step) {
    const terminals: Array<
        | InputTerminal
        | InputCollectionTerminal
        | InputParameterTerminal
        | OutputParameterTerminal
        | OutputCollectionTerminal
        | OutputParameterTerminal
    > = [];
    step.inputs?.map((input) => {
        const terminalArgs = {
            datatypesMapper: testDatatypesMapper,
            name: input.name,
            stepId: step.id,
        };
        const inputArgs = {
            datatypes: input.extensions,
            multiple: input.multiple,
            optional: input.optional,
        };
        if (input.input_type === "dataset") {
            terminals.push(
                new InputTerminal({
                    ...terminalArgs,
                    // kind of silly, class is input after all ?
                    type: "input",
                    input: inputArgs,
                })
            );
        } else if (input.input_type === "dataset_collection") {
            terminals.push(
                new InputCollectionTerminal({
                    ...terminalArgs,
                    type: "input",
                    collection_types: input.collection_types,
                    input: {
                        ...inputArgs,
                    },
                })
            );
        } else if (input.input_type === "parameter") {
            terminals.push(
                new InputParameterTerminal({
                    ...terminalArgs,
                    type: "input",
                    input: {
                        ...inputArgs,
                    },
                })
            );
        }
    });
    step.outputs.map((output) => {
        const outputArgs = {
            name: output.name,
            datatypes: output.extensions,
            optional: output.optional,
            stepId: step.id,
            type: "output",
        };
        if ("parameter" in output) {
            // new OutputParameterTerminal({
            // })
        }
    });
}

describe("terminal map over", () => {
    let stepStore: ReturnType<typeof useWorkflowStepStore>;
    let connectionStore: ReturnType<typeof useConnectionStore>;
    let inputTerminals: InputTerminal[] = [];
    let outputTerminals: OutputTerminal[] = [];
    beforeEach(() => {
        setActivePinia(createPinia());
        stepStore = useWorkflowStepStore();
        connectionStore = useConnectionStore();
        inputTerminals = [];
        outputTerminals = [];
        Object.entries(simpleSteps).map(([key, step]) => {
            stepStore.addStep(step);
            step.inputs?.map((input) => {
                const inputTerminal = new InputTerminal({
                    datatypesMapper: testDatatypesMapper,
                    stepId: step.id,
                    name: input.name,
                    type: "input",
                    input: { ...input, datatypes: input.extensions },
                });
                inputTerminals.push(inputTerminal);
            });
            step.outputs?.map((output) => {
                const outputTerminal = new OutputTerminal({
                    name: output.name,
                    stepId: step.id,
                    datatypes: output.extensions,
                    optional: output.optional,
                    type: "output",
                });
                outputTerminals.push(outputTerminal);
            });
        });
    });

    it("has step", () => {
        expect(stepStore.getStep(1)).toEqual(simpleSteps["1"]);
    });
    it("infers correct state", () => {
        const firstInputTerminal = inputTerminals[0];
        expect(firstInputTerminal.connections.length).toBe(1);
        expect(firstInputTerminal.mapOver).toBe(null);
        expect(firstInputTerminal.isMappedOver()).toBe(false);
        expect(firstInputTerminal.hasConnectedMappedInputTerminals()).toBe(false);
        expect(firstInputTerminal.hasMappedOverInputTerminals()).toBe(false);
        expect(firstInputTerminal.hasConnectedOutputTerminals()).toBe(false);
        const canAccept = firstInputTerminal.canAccept(outputTerminals[0]);
        expect(canAccept.canAccept).toBe(false);
        expect(canAccept.reason).toBe(
            "Input already filled with another connection, delete it before connecting another output."
        );
        // bypasses _inputFilled check
        expect(firstInputTerminal.attachable(outputTerminals[1]).canAccept).toBe(true);
        expect(firstInputTerminal.connected()).toBe(true);
        expect(firstInputTerminal._collectionAttached()).toBe(false);
        expect(firstInputTerminal._producesAcceptableDatatype(outputTerminals[1]).canAccept).toBe(true);
    });
    it("can accept new connection", () => {
        const firstInputTerminal = inputTerminals[0];
        const connection = firstInputTerminal.connections[0];
        expect(firstInputTerminal.canAccept(outputTerminals[0]).canAccept).toBe(false);
        connectionStore.removeConnection(connection.id);
        expect(firstInputTerminal.canAccept(outputTerminals[0]).canAccept).toBe(true);
        connectionStore.addConnection(connection);
        expect(firstInputTerminal.canAccept(outputTerminals[0]).canAccept).toBe(false);
    });
});
