import { setActivePinia, createPinia } from "pinia";

import { useWorkflowStepStore, type Step } from "@/stores/workflowStepStore";
import {
    terminalFactory,
    InputCollectionTerminal,
    InputTerminal,
    InputParameterTerminal,
    OutputCollectionTerminal,
    OutputTerminal,
    OutputParameterTerminal,
} from "./terminals";
import * as _simpleSteps from "../test-data/simple_steps.json";
import * as _advancedSteps from "../test-data/parameter_steps.json";
import { testDatatypesMapper } from "@/components/Datatypes/test_fixtures";
import { useConnectionStore } from "@/stores/workflowConnectionStore";

const simpleSteps = _simpleSteps as { [index: string]: Step };
const advancedSteps = _advancedSteps as { [index: string]: Step };

describe("terminalFactory", () => {
    let terminals: { [index: string]: { [index: string]: ReturnType<typeof terminalFactory> } } = {};
    beforeEach(() => {
        setActivePinia(createPinia());
        Object.entries(advancedSteps).map(([key, step]) => {
            const stepLabel = step.label;
            if (stepLabel) {
                terminals[stepLabel] = {};
                step.inputs?.map((input) => {
                    terminals[stepLabel][input.name] = terminalFactory(step.id, input, testDatatypesMapper);
                });
                step.outputs?.map((output) => {
                    terminals[stepLabel][output.name] = terminalFactory(step.id, output, testDatatypesMapper);
                });
            }
        });
    });

    it("constructs correct class instances", () => {
        expect(terminals["data input"]["output"]).toBeInstanceOf(OutputTerminal);
        expect(terminals["simple data"]["input"]).toBeInstanceOf(InputTerminal);
        expect(terminals["simple data"]["out_file1"]).toBeInstanceOf(OutputTerminal);
        expect(terminals["list input"]["output"]).toBeInstanceOf(OutputCollectionTerminal);
        expect(terminals["list:list input"]["output"]).toBeInstanceOf(OutputCollectionTerminal);
        expect(terminals["multi data"]["f1"]).toBeInstanceOf(InputTerminal);
        expect(terminals["multi data"]["f2"]).toBeInstanceOf(InputTerminal);
        expect(terminals["multi data"]["out1"]).toBeInstanceOf(OutputTerminal);
        expect(terminals["multi data"]["out2"]).toBeInstanceOf(OutputTerminal);
        expect(terminals["integer parameter input"]["output"]).toBeInstanceOf(OutputParameterTerminal);
        expect(terminals["any collection"]["input"]).toBeInstanceOf(InputCollectionTerminal);
        expect(terminals["any collection"]["output"]).toBeInstanceOf(OutputCollectionTerminal);
    });
});

describe("Input terminal", () => {
    let stepStore: ReturnType<typeof useWorkflowStepStore>;
    let connectionStore: ReturnType<typeof useConnectionStore>;
    let terminals: { [index: number]: { [index: string]: ReturnType<typeof terminalFactory> } } = {};
    beforeEach(() => {
        setActivePinia(createPinia());
        stepStore = useWorkflowStepStore();
        connectionStore = useConnectionStore();
        Object.entries(simpleSteps).map(([key, step]) => {
            stepStore.addStep(step);
            terminals[step.id] = {};
            const stepTerminals = terminals[step.id];
            step.inputs?.map((input) => {
                stepTerminals[input.name] = terminalFactory(step.id, input, testDatatypesMapper);
            });
            step.outputs?.map((output) => {
                stepTerminals[output.name] = terminalFactory(step.id, output, testDatatypesMapper);
            });
        });
    });

    it("has step", () => {
        expect(stepStore.getStep(1)).toEqual(simpleSteps["1"]);
    });
    it("infers correct state", () => {
        const firstInputTerminal = terminals[1]["input"] as InputTerminal;
        expect(firstInputTerminal).toBeInstanceOf(InputTerminal);
        const dataInputOutputTerminal = terminals[0]["output"] as OutputTerminal;
        expect(dataInputOutputTerminal).toBeInstanceOf(OutputTerminal);
        expect(firstInputTerminal.connections.length).toBe(1);
        expect(firstInputTerminal.mapOver).toBe(null);
        expect(firstInputTerminal.isMappedOver()).toBe(false);
        expect(firstInputTerminal.hasConnectedMappedInputTerminals()).toBe(false);
        expect(firstInputTerminal.hasMappedOverInputTerminals()).toBe(false);
        expect(firstInputTerminal.hasConnectedOutputTerminals()).toBe(false);
        const canAccept = firstInputTerminal.canAccept(dataInputOutputTerminal);
        expect(canAccept.canAccept).toBe(false);
        expect(canAccept.reason).toBe(
            "Input already filled with another connection, delete it before connecting another output."
        );
        // bypasses _inputFilled check
        expect(firstInputTerminal.attachable(dataInputOutputTerminal).canAccept).toBe(true);
        expect(firstInputTerminal.connected()).toBe(true);
        expect(firstInputTerminal._collectionAttached()).toBe(false);
        expect(firstInputTerminal._producesAcceptableDatatype(dataInputOutputTerminal).canAccept).toBe(true);
    });
    it("can accept new connection", () => {
        const firstInputTerminal = terminals[1]["input"] as InputTerminal;
        const dataInputOutputTerminal = terminals[0]["output"] as OutputTerminal;
        const connection = firstInputTerminal.connections[0];
        expect(firstInputTerminal.canAccept(dataInputOutputTerminal).canAccept).toBe(false);
        connectionStore.removeConnection(connection.id);
        expect(firstInputTerminal.canAccept(dataInputOutputTerminal).canAccept).toBe(true);
        connectionStore.addConnection(connection);
        expect(firstInputTerminal.canAccept(dataInputOutputTerminal).canAccept).toBe(false);
    });
});
