import { setActivePinia, createPinia } from "pinia";

import { useWorkflowStepStore } from "@/stores/workflowStepStore";
import { InputTerminal, OutputTerminal } from "./terminals";
import * as steps from "../test-data/simple_steps.json";
import { testDatatypesMapper } from "@/components/Datatypes/test_fixtures";
import { useConnectionStore } from "@/stores/workflowConnectionStore";

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
        Object.entries(steps).map(([key, step]) => {
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
        expect(stepStore.getStep(1)).toEqual(steps["1"]);
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
