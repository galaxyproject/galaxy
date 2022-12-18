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
import { NULL_COLLECTION_TYPE_DESCRIPTION } from "./collectionTypeDescription";

const simpleSteps = _simpleSteps as { [index: string]: Step };
const advancedSteps = _advancedSteps as { [index: string]: Step };

function setupAdvanced() {
    const terminals: { [index: string]: { [index: string]: ReturnType<typeof terminalFactory> } } = {};
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
    return terminals;
}

describe("terminalFactory", () => {
    let terminals: { [index: string]: { [index: string]: ReturnType<typeof terminalFactory> } } = {};
    beforeEach(() => {
        setActivePinia(createPinia());
        terminals = setupAdvanced();
    });

    it("constructs correct class instances", () => {
        expect(terminals["data input"]["output"]).toBeInstanceOf(OutputTerminal);
        expect(terminals["simple data"]["input"]).toBeInstanceOf(InputTerminal);
        expect(terminals["simple data"]["out_file1"]).toBeInstanceOf(OutputTerminal);
        expect(terminals["simple data 2"]["out_file1"]).toBeInstanceOf(OutputTerminal);
        expect(terminals["optional data input"]["output"]).toBeInstanceOf(OutputTerminal);
        expect(terminals["list input"]["output"]).toBeInstanceOf(OutputCollectionTerminal);
        expect(terminals["list:list input"]["output"]).toBeInstanceOf(OutputCollectionTerminal);
        expect(terminals["paired input"]["output"]).toBeInstanceOf(OutputCollectionTerminal);
        expect(terminals["multi data"]["f1"]).toBeInstanceOf(InputTerminal);
        expect(terminals["multi data"]["f2"]).toBeInstanceOf(InputTerminal);
        expect(terminals["multi data"]["out1"]).toBeInstanceOf(OutputTerminal);
        expect(terminals["multi data"]["out2"]).toBeInstanceOf(OutputTerminal);
        expect(terminals["integer parameter input"]["output"]).toBeInstanceOf(OutputParameterTerminal);
        expect(terminals["any collection"]["input"]).toBeInstanceOf(InputCollectionTerminal);
        expect(terminals["any collection"]["output"]).toBeInstanceOf(OutputCollectionTerminal);
        expect(terminals["multi data"]["advanced|advanced_threshold"]).toBeInstanceOf(InputParameterTerminal);
        expect(terminals["list collection input"]["input1"]).toBeInstanceOf(InputCollectionTerminal);
    });
});

describe("canAccept", () => {
    let terminals: { [index: string]: { [index: string]: ReturnType<typeof terminalFactory> } } = {};
    let stepStore: ReturnType<typeof useWorkflowStepStore>;
    let connectionStore: ReturnType<typeof useConnectionStore>;
    beforeEach(() => {
        setActivePinia(createPinia());
        terminals = setupAdvanced();
        stepStore = useWorkflowStepStore();
        Object.entries(advancedSteps).map(([key, step]) => {
            stepStore.addStep(step);
        });
    });

    it("accepts simple data -> data connections", () => {
        const dataOut = terminals["data input"]["output"] as OutputTerminal;
        const dataIn = terminals["simple data"]["input"] as InputTerminal;
        expect(dataIn.canAccept(dataOut).canAccept).toBe(true);
        dataIn.connect(dataOut);
        expect(dataIn.canAccept(dataOut).canAccept).toBe(false);
        dataIn.disconnect(dataOut);
        expect(dataIn.canAccept(dataOut).canAccept).toBe(true);
    });
    it("accepts collection data -> data connection", () => {
        const collectionOut = terminals["list input"]["output"] as OutputCollectionTerminal;
        const dataIn = terminals["simple data"]["input"] as InputTerminal;
        expect(dataIn.mapOver).toBe(NULL_COLLECTION_TYPE_DESCRIPTION);
        expect(dataIn.canAccept(collectionOut).canAccept).toBe(true);
        dataIn.connect(collectionOut);
        expect(dataIn.mapOver).toEqual({ collectionType: "list", isCollection: true, rank: 1 });
        expect(dataIn.canAccept(collectionOut).canAccept).toBe(false);
        dataIn.disconnect(collectionOut);
        expect(dataIn.canAccept(collectionOut).canAccept).toBe(true);
        expect(dataIn.mapOver).toEqual(NULL_COLLECTION_TYPE_DESCRIPTION);
    });
    it("accepts list:list data -> data connection", () => {
        const collectionOut = terminals["list:list input"]["output"] as OutputCollectionTerminal;
        const dataIn = terminals["simple data"]["input"] as InputTerminal;
        expect(dataIn.mapOver).toBe(NULL_COLLECTION_TYPE_DESCRIPTION);
        expect(dataIn.canAccept(collectionOut).canAccept).toBe(true);
        dataIn.connect(collectionOut);
        expect(dataIn.mapOver).toEqual({ collectionType: "list:list", isCollection: true, rank: 2 });
        expect(dataIn.canAccept(collectionOut).canAccept).toBe(false);
        dataIn.disconnect(collectionOut);
        expect(dataIn.canAccept(collectionOut).canAccept).toBe(true);
        expect(dataIn.mapOver).toEqual(NULL_COLLECTION_TYPE_DESCRIPTION);
    });
    it("treats multi data input as list input", () => {
        const collectionOut = terminals["list input"]["output"] as OutputCollectionTerminal;
        const multiDataIn = terminals["multi data"]["f1"] as InputTerminal;
        expect(multiDataIn.canAccept(collectionOut).canAccept).toBe(true);
        multiDataIn.connect(collectionOut);
        expect(multiDataIn.mapOver).toBe(NULL_COLLECTION_TYPE_DESCRIPTION);
    });
    it("rejects paired input on multi-data input", () => {
        const multiDataIn = terminals["multi data"]["f1"] as InputTerminal;
        const pairedOut = terminals["paired input"]["output"] as OutputCollectionTerminal;
        expect(multiDataIn.canAccept(pairedOut).canAccept).toBe(false);
        expect(multiDataIn.canAccept(pairedOut).reason).toBe(
            "Cannot attach paired inputs to multiple data parameters, only lists may be treated this way."
        );
    }),
        it("rejects collections on multi data inputs if non-collection already connected", () => {
            const multiDataIn = terminals["multi data"]["f1"] as InputTerminal;
            const dataOut = terminals["data input"]["output"] as OutputTerminal;
            const collectionOut = terminals["list input"]["output"] as OutputCollectionTerminal;
            multiDataIn.connect(dataOut);
            expect(multiDataIn.canAccept(collectionOut).canAccept).toBe(false);
            expect(multiDataIn.canAccept(collectionOut).reason).toBe(
                "Cannot attach collections to data parameters with individual data inputs already attached."
            );
        });
    it("maps list:list over multi data input", () => {
        const collectionOut = terminals["list:list input"]["output"] as OutputCollectionTerminal;
        const multiDataIn = terminals["multi data"]["f1"] as InputTerminal;
        expect(multiDataIn.canAccept(collectionOut).canAccept).toBe(true);
        multiDataIn.connect(collectionOut);
        expect(multiDataIn.mapOver).toEqual({ collectionType: "list", isCollection: true, rank: 1 });
    });
    it("rejects attaching multiple collections to a single multi data input", () => {
        const collectionOut = terminals["list:list input"]["output"] as OutputCollectionTerminal;
        const otherCollectionOut = terminals["list:list input"]["output"] as OutputCollectionTerminal;
        const multiDataIn = terminals["multi data"]["f1"] as InputTerminal;
        multiDataIn.connect(collectionOut);
        expect(multiDataIn.canAccept(otherCollectionOut).canAccept).toBe(false);
        expect(multiDataIn.canAccept(otherCollectionOut).reason).toBe(
            "Input already filled with another connection, delete it before connecting another output."
        );
    });
    it("rejects data -> collection connection", () => {
        const dataOut = terminals["data input"]["output"] as OutputTerminal;
        const collectionInput = terminals["any collection"]["input"] as InputCollectionTerminal;
        expect(collectionInput.canAccept(dataOut).canAccept).toBe(false);
        expect(collectionInput.canAccept(dataOut).reason).toBe("Cannot attach a data output to a collection input.");
    });
    it("rejects optional data -> required data", () => {
        const optionalDataOut = terminals["optional data input"]["output"] as OutputTerminal;
        const dataIn = terminals["simple data"]["input"] as InputTerminal;
        expect(dataIn.canAccept(optionalDataOut).canAccept).toBe(false);
        expect(dataIn.canAccept(optionalDataOut).reason).toBe(
            "Cannot connect an optional output to a non-optional input"
        );
    });
    it("rejects parameter to data connection", () => {
        const dataIn = terminals["simple data"]["input"] as InputTerminal;
        // # type system would reject this, but test runtime too
        const integerParam = terminals["integer parameter input"]["output"] as any;
        expect(dataIn.canAccept(integerParam).canAccept).toBe(false);
        expect(dataIn.canAccept(integerParam).reason).toBe("Cannot connect workflow parameter to data input.");
    });
    it("rejects data to parameter connection", () => {
        const dataOut = terminals["data input"]["output"] as OutputTerminal;
        const integerInputParam = terminals["multi data"]["advanced|advanced_threshold"] as InputParameterTerminal;
        expect(integerInputParam.canAccept(dataOut).canAccept).toBe(false);
        expect(integerInputParam.canAccept(dataOut).reason).toBe("Cannot attach a data parameter to a integer input");
    });
    it("tracks transitive map over", () => {
        const collectionOut = terminals["list:list input"]["output"] as OutputCollectionTerminal;
        const dataIn = terminals["simple data"]["input"] as InputTerminal;
        const simpleDataOut = terminals["simple data"]["out_file1"] as OutputTerminal;
        dataIn.connect(collectionOut);
        expect(dataIn.mapOver).toEqual({ collectionType: "list:list", isCollection: true, rank: 2 });
        const otherDataIn = terminals["multi data"]["f1"] as InputTerminal;
        expect(otherDataIn.canAccept(simpleDataOut).canAccept).toBe(true);
        otherDataIn.connect(simpleDataOut);
        expect(otherDataIn.mapOver).toEqual({ collectionType: "list", isCollection: true, rank: 1 });
        const otherDataInTwo = terminals["multi data"]["f2"] as InputTerminal;
        expect(otherDataInTwo.canAccept(collectionOut).canAccept).toBe(false);
        expect(otherDataInTwo.canAccept(collectionOut).reason).toBe(
            "Can't map over this input with output collection type - other inputs have an incompatible map over collection type. Disconnect inputs (and potentially outputs) and retry."
        );
    });
    it("tracks transitive map over through collection inputs", () => {
        const collectionOut = terminals["list:list input"]["output"] as OutputCollectionTerminal;
        const collectionIn = terminals["list collection input"]["input1"] as InputCollectionTerminal;
        expect(collectionIn.canAccept(collectionOut).canAccept).toBe(true);
        collectionIn.connect(collectionOut);
        expect(collectionIn.mapOver).toEqual({ collectionType: "list", isCollection: true, rank: 1 });
        const intermediateOut = terminals["list collection input"]["out_file1"] as OutputCollectionTerminal;
        const otherListIn = terminals["list collection input 2"]["input1"] as InputCollectionTerminal;
        expect(otherListIn.canAccept(intermediateOut).canAccept).toBe(true);
        otherListIn.connect(intermediateOut);
        expect(otherListIn.mapOver).toEqual(NULL_COLLECTION_TYPE_DESCRIPTION);
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
        expect(firstInputTerminal.mapOver).toBe(NULL_COLLECTION_TYPE_DESCRIPTION);
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
