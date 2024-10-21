import EventEmitter from "events";

import { type DatatypesMapperModel } from "@/components/Datatypes/model";
import { type useWorkflowStores } from "@/composables/workflowStores";
import { type Connection, type ConnectionId, getConnectionId } from "@/stores/workflowConnectionStore";
import {
    type CollectionOutput,
    type DataCollectionStepInput,
    type DataOutput,
    type DataStepInput,
    type ParameterOutput,
    type ParameterStepInput,
    type TerminalSource,
} from "@/stores/workflowStepStore";
import { assertDefined } from "@/utils/assertions";

import {
    ANY_COLLECTION_TYPE_DESCRIPTION,
    CollectionTypeDescription,
    type CollectionTypeDescriptor,
    NULL_COLLECTION_TYPE_DESCRIPTION,
} from "./collectionTypeDescription";

export class ConnectionAcceptable {
    reason: string | null;
    canAccept: boolean;
    constructor(canAccept: boolean, reason: string | null) {
        this.canAccept = canAccept;
        this.reason = reason;
    }
}

interface BaseTerminalArgs {
    name: string;
    stepId: number;
    datatypesMapper: DatatypesMapperModel;
    stores: ReturnType<typeof useWorkflowStores>;
}

interface InputTerminalInputs {
    datatypes: string[];
    multiple: boolean;
    optional: boolean;
}

interface InputTerminalArgs extends BaseTerminalArgs {
    input: InputTerminalInputs;
    input_type: "dataset" | "dataset_collection" | "parameter";
}

class Terminal extends EventEmitter {
    stores;
    name: string;
    multiple: boolean;
    stepId: number;
    terminalType: "input" | "output";
    datatypesMapper: DatatypesMapperModel;
    localMapOver: CollectionTypeDescriptor;

    constructor(attr: BaseTerminalArgs) {
        super();
        this.stores = attr.stores;
        this.stepId = attr.stepId;
        this.name = attr.name;
        this.multiple = false;
        this.terminalType = "input";
        this.datatypesMapper = attr.datatypesMapper;
        this.localMapOver = NULL_COLLECTION_TYPE_DESCRIPTION;
    }
    public get id() {
        return `node-${this.stepId}-${this.terminalType}-${this.name}`;
    }
    public get connections(): Connection[] {
        return this.stores.connectionStore.getConnectionsForTerminal(this.id);
    }
    public get mapOver(): CollectionTypeDescriptor {
        return this.stores.stepStore.stepMapOver[this.stepId] || NULL_COLLECTION_TYPE_DESCRIPTION;
    }
    buildConnection(other: Terminal | Connection) {
        let connection: Connection;
        if (other instanceof Terminal) {
            connection = {
                input: { stepId: this.stepId, name: this.name, connectorType: "input" },
                output: { stepId: other.stepId, name: other.name, connectorType: "output" },
            };
        } else {
            connection = other;
        }
        return connection;
    }
    connect(other: Terminal | Connection) {
        this.stores.undoRedoStore
            .action()
            .onRun(() => this.makeConnection(other))
            .onUndo(() => this.dropConnection(other))
            .setName("connect steps")
            .apply();
    }
    makeConnection(other: Terminal | Connection) {
        const connection = this.buildConnection(other);
        this.stores.connectionStore.addConnection(connection);
    }
    disconnect(other: Terminal | Connection) {
        this.stores.undoRedoStore
            .action()
            .onRun(() => this.dropConnection(other))
            .onUndo(() => this.makeConnection(other))
            .setName("disconnect steps")
            .apply();
    }
    dropConnection(other: Terminal | Connection) {
        const connection = this.buildConnection(other);
        this.stores.connectionStore.removeConnection(getConnectionId(connection));
        this.resetMappingIfNeeded(connection);
    }
    setMapOver(val: CollectionTypeDescriptor) {
        // we use this method to determine the map over status based on all terminals connected to this step
        let outputVal = val;
        if (this.multiple) {
            // emulate list input
            const description = new CollectionTypeDescription("list");
            if (val.collectionType === description.collectionType) {
                // No mapping over necessary
                return;
            }
            outputVal = val.effectiveMapOver(description);
        }

        const effectiveMapOver = this._effectiveMapOver(outputVal);

        if (!this.localMapOver.equal(effectiveMapOver)) {
            this.stores.stepStore.changeStepInputMapOver(this.stepId, this.name, effectiveMapOver);
            this.localMapOver = effectiveMapOver;
        }

        if (
            !this.mapOver.equal(effectiveMapOver) &&
            (effectiveMapOver.isCollection ||
                !Object.values(this.stores.stepStore.stepInputMapOver[this.stepId] ?? []).find(
                    (mapOver) => mapOver.isCollection
                ))
        ) {
            this.stores.stepStore.changeStepMapOver(this.stepId, effectiveMapOver);
        }
    }
    _effectiveMapOver(otherCollectionType: CollectionTypeDescriptor) {
        return otherCollectionType;
    }
    isMappedOver(): boolean {
        return Boolean(this.mapOver.isCollection);
    }
    resetMapping(_connection?: Connection) {
        this.stores.stepStore.changeStepMapOver(this.stepId, NULL_COLLECTION_TYPE_DESCRIPTION);
        this.stores.stepStore.resetStepInputMapOver(this.stepId);
    }
    hasConnectedMappedInputTerminals() {
        // check if step has connected and mapped input terminals ... should maybe be on step/node ?
        const connections = this.stores.connectionStore.getConnectionsForStep(this.stepId);
        return connections.some(
            (connection) =>
                connection.input.stepId === this.stepId &&
                this.stores.stepStore.stepMapOver[this.stepId]?.collectionType
        );
    }
    _getOutputConnections() {
        return this.stores.connectionStore.getConnectionsForStep(this.stepId).filter((connection) => {
            return connection.output.stepId === this.stepId;
        });
    }
    hasConnectedOutputTerminals() {
        // Does this step/node have connected connections
        return this._getOutputConnections().length > 0;
    }
    hasMappedOverInputTerminals() {
        return Boolean(this.stores.stepStore.stepMapOver[this.stepId]?.collectionType);
    }
    resetMappingIfNeeded(connection?: Connection) {
        const mapOver = this.mapOver;
        if (!mapOver.isCollection) {
            return;
        }
        // No output terminals are counting on this being mapped
        // over if connected inputs are still mapped over or if none
        // of the outputs are connected...
        const reset = !this.hasConnectedOutputTerminals();
        if (reset) {
            this.resetMapping(connection);
        }
    }
}

class BaseInputTerminal extends Terminal {
    datatypes: InputTerminalInputs["datatypes"];
    optional: InputTerminalInputs["optional"];
    localMapOver: CollectionTypeDescriptor;

    constructor(attr: InputTerminalArgs) {
        super(attr);
        this.datatypes = attr.input.datatypes;
        this.multiple = attr.input.multiple;
        this.optional = attr.input.optional;
        if (
            this.stores.stepStore.stepInputMapOver[this.stepId] &&
            this.stores.stepStore.stepInputMapOver[this.stepId]?.[this.name]
        ) {
            this.localMapOver = this.stores.stepStore.stepInputMapOver[this.stepId]![this.name]!;
        } else {
            this.localMapOver = NULL_COLLECTION_TYPE_DESCRIPTION;
        }
    }
    connect(other: BaseOutputTerminal): void {
        super.connect(other);
        this.setDefaultMapOver(other);
    }
    setDefaultMapOver(other: BaseOutputTerminal) {
        const otherCollectionType = this._otherCollectionType(other);
        if (otherCollectionType.isCollection) {
            return this.setMapOver(otherCollectionType);
        }
    }
    getStepMapOver() {
        this.getConnectedTerminals().forEach((other) => {
            this.setDefaultMapOver(other);
        });
    }

    canAccept(outputTerminal: BaseOutputTerminal) {
        if (this.stepId == outputTerminal.stepId) {
            return new ConnectionAcceptable(false, "Cannot connect output to input of same step.");
        }
        if (this._inputFilled()) {
            return new ConnectionAcceptable(
                false,
                "Input already filled with another connection, delete it before connecting another output."
            );
        } else {
            return this.attachable(outputTerminal);
        }
    }
    attachable(_terminal: BaseOutputTerminal): ConnectionAcceptable {
        // TODO: provide through Mixin
        throw Error("Subclass needs to implement this");
    }
    _getOutputStepsMapOver() {
        const connections = this._getOutputConnections();
        const connectedStepIds = Array.from(new Set(connections.map((connection) => connection.output.stepId)));
        return connectedStepIds.map(
            (stepId) => this.stores.stepStore.stepMapOver[stepId] || NULL_COLLECTION_TYPE_DESCRIPTION
        );
    }
    resetMapping(connection?: Connection) {
        super.resetMapping(connection);
        this.stores.stepStore.changeStepInputMapOver(this.stepId, this.name, NULL_COLLECTION_TYPE_DESCRIPTION);
        const outputStepIds = this._getOutputTerminals().map((outputTerminal) => outputTerminal.stepId);
        if (connection) {
            outputStepIds.push(connection.output.stepId);
        }
        Array.from(new Set(outputStepIds)).forEach((stepId) => {
            const step = this.stores.stepStore.getStep(stepId);
            if (step) {
                // step must have an output, since it is or was connected to this step
                const terminalSource = step.outputs[0];
                if (terminalSource) {
                    const terminal = terminalFactory(step.id, terminalSource, this.datatypesMapper, this.stores);
                    // drop mapping restrictions
                    terminal.resetMappingIfNeeded();
                    // re-establish map over through inputs
                    step.inputs.forEach((input) => {
                        terminalFactory(step.id, input, this.datatypesMapper, this.stores).getStepMapOver();
                    });
                }
            } else {
                console.error(`Invalid step. Could not fine step with id ${stepId} in store.`);
            }
        });
    }
    _getOutputTerminals() {
        return this.stores.connectionStore.getOutputTerminalsForInputTerminal(this.id);
    }
    _getFirstOutputTerminal() {
        const outputTerminals = this._getOutputTerminals();
        if (outputTerminals.length > 0) {
            return outputTerminals[0];
        }
        return null;
    }

    isMappedOver(): boolean {
        return Boolean(this.localMapOver.isCollection);
    }

    connected() {
        return Boolean(this._getFirstOutputTerminal());
    }
    _inputFilled() {
        let inputFilled: boolean;
        if (!this.connected()) {
            inputFilled = false;
        } else {
            if (this.multiple) {
                // Can only attach one collection to multiple input
                // data parameter.
                inputFilled = !!this._collectionAttached();
            } else {
                inputFilled = true;
            }
        }
        return inputFilled;
    }
    _collectionAttached() {
        const outputTerminals = this._getOutputTerminals();
        return outputTerminals.some((outputTerminal) => {
            const step = this.stores.stepStore.getStep(outputTerminal.stepId);

            if (!step) {
                console.error(`Invalid step. Could not find step with id ${outputTerminal.stepId} in store.`);
                return false;
            }

            const output = step.outputs.find((output) => output.name == outputTerminal.name);

            if (
                output &&
                (("collection" in output && output.collection) ||
                    this.stores.stepStore.stepMapOver[outputTerminal.stepId]?.isCollection ||
                    ("extensions" in output && output.extensions.indexOf("input") > 0))
            ) {
                return true;
            }
        });
    }
    _mappingConstraints() {
        // If this is a connected terminal, return list of collection types
        // other terminals connected to node are constraining mapping to.
        if (this.mapOver.isCollection) {
            return [this.mapOver];
        }
        return this._getOutputStepsMapOver();
    }
    _producesAcceptableDatatype(other: BaseOutputTerminal) {
        // other is a non-collection output...

        if (other instanceof OutputParameterTerminal) {
            return new ConnectionAcceptable(false, "Cannot connect workflow parameter to data input.");
        }
        return producesAcceptableDatatype(this.datatypesMapper, this.datatypes, other.datatypes);
    }
    _producesAcceptableDatatypeAndOptionalness(other: BaseOutputTerminal) {
        if (!this.optional && !this.multiple && other.optional) {
            return new ConnectionAcceptable(false, "Cannot connect an optional output to a non-optional input");
        }
        return this._producesAcceptableDatatype(other);
    }
    _otherCollectionType(other: BaseOutputTerminal) {
        let otherCollectionType = NULL_COLLECTION_TYPE_DESCRIPTION;
        if (other.isCollection && other.collectionType) {
            otherCollectionType = other.collectionType;
        }
        const otherMapOver = other.mapOver;
        if (otherMapOver.isCollection) {
            otherCollectionType = otherMapOver.append(otherCollectionType);
        }
        return otherCollectionType;
    }
    getConnectedTerminals() {
        return this.connections.map((connection) => {
            const outputStep = this.stores.stepStore.getStep(connection.output.stepId);
            if (!outputStep) {
                return new InvalidOutputTerminal({
                    stepId: -1,
                    optional: false,
                    datatypes: [],
                    name: connection.output.name,
                    valid: false,
                    datatypesMapper: this.datatypesMapper,
                    stores: this.stores,
                });
            }
            let terminalSource = outputStep.outputs.find((output) => output.name === connection.output.name);
            if (!terminalSource) {
                return new InvalidOutputTerminal({
                    stepId: -1,
                    optional: false,
                    datatypes: [],
                    name: connection.output.name,
                    valid: false,
                    datatypesMapper: this.datatypesMapper,
                    stores: this.stores,
                });
            }
            const postJobActionKey = `ChangeDatatypeAction${connection.output.name}`;
            if (
                "extensions" in terminalSource &&
                outputStep.post_job_actions &&
                postJobActionKey in outputStep.post_job_actions
            ) {
                const extensionType = outputStep.post_job_actions![postJobActionKey]!.action_arguments.newtype;

                (terminalSource as DataOutput | CollectionOutput) = {
                    ...terminalSource,
                    extensions: extensionType ? [extensionType] : [],
                };
            }

            return terminalFactory(outputStep.id, terminalSource, this.datatypesMapper, this.stores);
        });
    }

    getInvalidConnectedTerminals() {
        return this.getConnectedTerminals().filter((terminal) => {
            const canAccept = this.attachable(terminal);
            const connectionId: ConnectionId = `${this.stepId}-${this.name}-${terminal.stepId}-${terminal.name}`;
            if (!canAccept.canAccept) {
                this.stores.connectionStore.markInvalidConnection(connectionId, canAccept.reason ?? "Unknown");
                return true;
            } else if (this.stores.connectionStore.invalidConnections[connectionId]) {
                this.stores.connectionStore.dropFromInvalidConnections(connectionId);
            }
            return false;
        });
    }

    destroyInvalidConnections() {
        this.getInvalidConnectedTerminals().forEach((terminal) => this.disconnect(terminal));
    }
}

interface InvalidInputTerminalArgs extends InputTerminalArgs {
    valid: false;
}

export class InvalidInputTerminal extends BaseInputTerminal {
    valid: false;
    localMapOver: CollectionTypeDescriptor;

    constructor(attr: InvalidInputTerminalArgs) {
        super(attr);
        this.valid = false;
        this.localMapOver = NULL_COLLECTION_TYPE_DESCRIPTION;
    }

    attachable(_terminal: BaseOutputTerminal) {
        return new ConnectionAcceptable(false, "Cannot attach to invalid input. Disconnect this input.");
    }
}

// TODO: turn into InputTerminalAttachableMixin ?
export class InputTerminal extends BaseInputTerminal {
    collection: boolean;

    constructor(attr: InputTerminalArgs) {
        super(attr);
        this.collection = false;
        this.getStepMapOver();
    }

    attachable(other: BaseOutputTerminal) {
        const otherCollectionType = this._otherCollectionType(other);
        const mapOver = this.mapOver;
        if (otherCollectionType.isCollection) {
            if (this.multiple) {
                if (this.connected() && !this._collectionAttached()) {
                    return new ConnectionAcceptable(
                        false,
                        "Cannot attach collections to data parameters with individual data inputs already attached."
                    );
                }
                if (otherCollectionType.collectionType && otherCollectionType.collectionType.endsWith("paired")) {
                    return new ConnectionAcceptable(
                        false,
                        "Cannot attach paired inputs to multiple data parameters, only lists may be treated this way."
                    );
                }
            }
            if (mapOver.isCollection && mapOver.canMatch(otherCollectionType)) {
                return this._producesAcceptableDatatypeAndOptionalness(other);
            } else if (
                this.multiple &&
                new CollectionTypeDescription("list").append(this.mapOver).canMatch(otherCollectionType)
            ) {
                // This handles the special case of a list input being connected to a multiple="true" data input.
                // Nested lists would be correctly mapped over by the above condition.
                return this._producesAcceptableDatatypeAndOptionalness(other);
            } else {
                //  Need to check if this would break constraints...
                const mappingConstraints = this._mappingConstraints();
                if (mappingConstraints.every(otherCollectionType.canMatch.bind(otherCollectionType))) {
                    return this._producesAcceptableDatatypeAndOptionalness(other);
                } else {
                    if (mapOver.isCollection) {
                        // incompatible collection type attached
                        if (this.hasConnectedMappedInputTerminals()) {
                            return new ConnectionAcceptable(
                                false,
                                "Can't map over this input with output collection type - other inputs have an incompatible map over collection type. Disconnect inputs (and potentially outputs) and retry."
                            );
                        } else {
                            return new ConnectionAcceptable(
                                false,
                                "Can't map over this input with output collection type - this step has outputs defined constraining the mapping of this tool. Disconnect outputs and retry."
                            );
                        }
                    } else {
                        return new ConnectionAcceptable(
                            false,
                            "Can't map over this input with output collection type - an output of this tool is mapped over constraining this input. Disconnect output(s) and retry."
                        );
                    }
                }
            }
        } else {
            if (this.localMapOver.isCollection) {
                return new ConnectionAcceptable(
                    false,
                    "Cannot attach non-collection output to mapped over input, consider disconnecting inputs and outputs to reset this input's mapping."
                );
            }
        }
        return this._producesAcceptableDatatypeAndOptionalness(other);
    }
}

interface InputParameterTerminalArgs extends InputTerminalArgs {
    type: ParameterStepInput["type"];
}

export class InputParameterTerminal extends BaseInputTerminal {
    type: ParameterStepInput["type"];

    constructor(attr: InputParameterTerminalArgs) {
        super(attr);
        this.type = attr.type;
        this.getStepMapOver();
    }

    effectiveType(parameterType: string) {
        let newType: string;
        switch (parameterType) {
            case "select":
                newType = "text";
                break;
            case "data_column":
                newType = "integer";
                break;
            default:
                newType = parameterType;
        }
        return newType;
    }
    attachable(other: BaseOutputTerminal) {
        const effectiveThisType = this.effectiveType(this.type);
        const otherType = ("type" in other && other.type) || "data";
        const effectiveOtherType = this.effectiveType(otherType);
        if (!this.optional && other.optional) {
            return new ConnectionAcceptable(false, `Cannot attach an optional output to a required parameter`);
        }
        const canAccept = effectiveThisType === effectiveOtherType;
        if (!this.multiple && other.multiple) {
            return new ConnectionAcceptable(
                false,
                `This output parameter represents multiple values but input only accepts a single value`
            );
        }
        return new ConnectionAcceptable(
            canAccept,
            canAccept ? null : `Cannot attach a ${effectiveOtherType} parameter to a ${effectiveThisType} input`
        );
    }
}

interface InputCollectionTerminalArgs extends InputTerminalArgs {
    collection_types: string[] | null;
}

export class InputCollectionTerminal extends BaseInputTerminal {
    collection: boolean;
    collectionTypes: CollectionTypeDescriptor[];

    constructor(attr: InputCollectionTerminalArgs) {
        super(attr);
        this.multiple = false;
        this.collection = true;
        this.collectionTypes = attr.collection_types
            ? attr.collection_types.map((collectionType) => new CollectionTypeDescription(collectionType))
            : [];
        if (!this.collectionTypes.length) {
            this.collectionTypes.push(ANY_COLLECTION_TYPE_DESCRIPTION);
        }
        this.getStepMapOver();
    }
    _effectiveMapOver(otherCollectionType: CollectionTypeDescriptor) {
        const collectionTypes = this.collectionTypes;
        const canMatch = collectionTypes.some((collectionType) => collectionType.canMatch(otherCollectionType));
        if (!canMatch) {
            for (const collectionTypeIndex in collectionTypes) {
                const collectionType = collectionTypes[collectionTypeIndex]!;

                if (otherCollectionType.canMapOver(collectionType)) {
                    const effectiveMapOver = otherCollectionType.effectiveMapOver(collectionType);

                    if (effectiveMapOver != NULL_COLLECTION_TYPE_DESCRIPTION) {
                        return effectiveMapOver;
                    }
                }
            }
        }
        return NULL_COLLECTION_TYPE_DESCRIPTION;
    }
    _effectiveCollectionTypes() {
        return this.collectionTypes.map((t) => this.localMapOver.append(t));
    }
    attachable(other: BaseOutputTerminal) {
        const otherCollectionType = this._otherCollectionType(other);
        if (otherCollectionType.isCollection) {
            const effectiveCollectionTypes = this._effectiveCollectionTypes();
            const mapOver = this.mapOver;
            const canMatch = effectiveCollectionTypes.some((effectiveCollectionType) =>
                effectiveCollectionType.canMatch(otherCollectionType)
            );
            if (canMatch) {
                // Only way a direct match...
                return this._producesAcceptableDatatypeAndOptionalness(other);
                // Otherwise we need to mapOver
            } else if (mapOver.isCollection) {
                // In this case, mapOver already set and we didn't match skipping...
                if (this.hasConnectedMappedInputTerminals()) {
                    return new ConnectionAcceptable(
                        false,
                        "Can't map over this input with output collection type - other inputs have an incompatible map over collection type. Disconnect inputs (and potentially outputs) and retry."
                    );
                } else {
                    return new ConnectionAcceptable(
                        false,
                        "Can't map over this input with output collection type - this step has outputs defined constraining the mapping of this tool. Disconnect outputs and retry."
                    );
                }
            } else if (this.collectionTypes.some((collectionType) => otherCollectionType.canMapOver(collectionType))) {
                // we're not mapped over - but hey maybe we could be... lets check.
                const effectiveMapOver = this._effectiveMapOver(otherCollectionType);
                //  Need to check if this would break constraints...
                const mappingConstraints = this._mappingConstraints();
                if (mappingConstraints.every((d) => effectiveMapOver.canMatch(d))) {
                    return this._producesAcceptableDatatypeAndOptionalness(other);
                } else {
                    return new ConnectionAcceptable(
                        false,
                        "Can't map over this input with output collection type - this step has outputs defined constraining the mapping of this tool. Disconnect outputs and retry."
                    );
                }
            } else {
                return new ConnectionAcceptable(false, "Incompatible collection type(s) for attachment.");
            }
        } else {
            return new ConnectionAcceptable(false, "Cannot attach a data output to a collection input.");
        }
    }
}

interface BaseOutputTerminalArgs extends BaseTerminalArgs {
    datatypes: string[];
    optional: boolean;
}

export type InputTerminalsAndInvalid = InputTerminals | InvalidInputTerminal;

class BaseOutputTerminal extends Terminal {
    datatypes: BaseOutputTerminalArgs["datatypes"];
    optional: BaseOutputTerminalArgs["optional"];
    isCollection?: boolean;
    collectionType?: CollectionTypeDescriptor;
    type?: string;

    constructor(attr: BaseOutputTerminalArgs) {
        super(attr);
        this.datatypes = attr.datatypes;
        this.optional = attr.optional || Boolean(this.stores.stepStore.getStep(this.stepId)?.when);
        this.terminalType = "output";
    }
    getConnectedTerminals(): InputTerminalsAndInvalid[] {
        return this.connections.map((connection) => {
            const inputStep = this.stores.stepStore.getStep(connection.input.stepId);
            assertDefined(inputStep, `Invalid step. Could not find step with id ${connection.input.stepId} in store.`);

            const extraStepInput = this.stores.stepStore.getStepExtraInputs(inputStep.id);
            const terminalSource = [...extraStepInput, ...inputStep.inputs].find(
                (input) => input.name === connection.input.name
            );
            if (!terminalSource) {
                return new InvalidInputTerminal({
                    valid: false,
                    name: connection.input.name,
                    stepId: connection.input.stepId,
                    datatypesMapper: this.datatypesMapper,
                    input_type: "dataset",
                    input: {
                        datatypes: [],
                        optional: false,
                        multiple: false,
                    },
                    stores: this.stores,
                });
            }
            return terminalFactory(inputStep.id, terminalSource, this.datatypesMapper, this.stores);
        });
    }

    getInvalidConnectedTerminals() {
        return this.getConnectedTerminals().filter((terminal: any) => {
            const canAccept = terminal.attachable(this);
            const connectionId: ConnectionId = `${terminal.stepId}-${terminal.name}-${this.stepId}-${this.name}`;
            if (!canAccept.canAccept) {
                this.stores.connectionStore.markInvalidConnection(connectionId, canAccept.reason ?? "Unknown");
                return true;
            } else if (this.stores.connectionStore.invalidConnections[connectionId]) {
                this.stores.connectionStore.dropFromInvalidConnections(connectionId);
            }
            return false;
        });
    }

    destroyInvalidConnections() {
        this.getConnectedTerminals().forEach((terminal) => {
            if (!terminal.attachable(this).canAccept) {
                terminal.disconnect(this);
            }
        });
    }
    validInputTerminals() {
        const validInputTerminals: InputTerminals[] = [];
        Object.values(this.stores.stepStore.steps).map((step) => {
            step.inputs?.forEach((input) => {
                const inputTerminal = terminalFactory(step.id, input, this.datatypesMapper, this.stores);
                if (inputTerminal.canAccept(this).canAccept) {
                    validInputTerminals.push(inputTerminal);
                }
            });
        });
        return validInputTerminals;
    }
}

export class OutputTerminal extends BaseOutputTerminal {}

interface OutputCollectionTerminalArgs extends BaseOutputTerminalArgs {
    collection_type: string;
    collection_type_source: string | null;
}

export class OutputCollectionTerminal extends BaseOutputTerminal {
    collectionTypeSource: string | null;

    constructor(attr: OutputCollectionTerminalArgs) {
        super(attr);
        this.collectionTypeSource = null;
        if (attr.collection_type) {
            this.collectionType = new CollectionTypeDescription(attr.collection_type);
        } else {
            this.collectionTypeSource = attr.collection_type_source;
            if (!this.collectionTypeSource) {
                console.log("Warning: No collection type or collection type source defined.");
            }
            this.collectionType = this.getCollectionTypeFromInput() || ANY_COLLECTION_TYPE_DESCRIPTION;
        }
        this.isCollection = true;
    }

    getCollectionTypeFromInput() {
        const connection = this.stores.connectionStore.connections.find(
            (connection) =>
                connection.input.name === this.collectionTypeSource && connection.input.stepId === this.stepId
        );
        if (connection) {
            const outputStep = this.stores.stepStore.getStep(connection.output.stepId);
            const inputStep = this.stores.stepStore.getStep(this.stepId);
            assertDefined(inputStep, `Invalid step. Could not find step with id ${connection.input.stepId} in store.`);

            if (outputStep) {
                const stepOutput = outputStep.outputs.find((output) => output.name == connection.output.name);
                const stepInput = inputStep.inputs.find((input) => input.name === this.collectionTypeSource);
                if (stepInput && stepOutput) {
                    const outputTerminal = terminalFactory(
                        connection.output.stepId,
                        stepOutput,
                        this.datatypesMapper,
                        this.stores
                    );
                    const inputTerminal = terminalFactory(
                        connection.output.stepId,
                        stepInput,
                        this.datatypesMapper,
                        this.stores
                    );
                    // otherCollectionType is the mapped over output collection as it would appear at the input terminal
                    const otherCollectionType = inputTerminal._otherCollectionType(outputTerminal);
                    // we need to find which of the possible input collection types is connected
                    if ("collectionTypes" in inputTerminal) {
                        // collection_type_source must point at input collection terminal
                        const connectedCollectionType = inputTerminal.collectionTypes.find(
                            (collectionType) =>
                                otherCollectionType.canMatch(collectionType) ||
                                otherCollectionType.canMapOver(collectionType)
                        );
                        if (connectedCollectionType) {
                            if (connectedCollectionType.collectionType === "any") {
                                // if the input collection type is "any" this output's collection type
                                // is exactly the same as the connected output
                                return otherCollectionType;
                            } else {
                                // else we pick the matching input collection type
                                // so that the map over logic applies correctly
                                return connectedCollectionType;
                            }
                        }
                    }
                }
            }
        }
        return ANY_COLLECTION_TYPE_DESCRIPTION;
    }
}

interface OutputParameterTerminalArgs extends Omit<BaseOutputTerminalArgs, "datatypes"> {
    type: ParameterOutput["type"];
    multiple: ParameterOutput["multiple"];
}

export class OutputParameterTerminal extends BaseOutputTerminal {
    constructor(attr: OutputParameterTerminalArgs) {
        super({ ...attr, datatypes: [] });
        this.type = attr.type;
        this.multiple = attr.multiple;
    }
}

interface InvalidOutputTerminalArgs extends BaseOutputTerminalArgs {
    valid: false;
}

export class InvalidOutputTerminal extends BaseOutputTerminal {
    valid: false;

    constructor(attr: InvalidOutputTerminalArgs) {
        super(attr);
        this.valid = false;
    }

    validInputTerminals() {
        return [];
    }

    canAccept() {
        return new ConnectionAcceptable(false, "Can't connect to invalid terminal.");
    }
}

export type OutputTerminals = OutputTerminal | OutputCollectionTerminal | OutputParameterTerminal;
export type InputTerminals = InputTerminal | InputCollectionTerminal | InputParameterTerminal;

export function producesAcceptableDatatype(
    datatypesMapper: DatatypesMapperModel,
    inputDatatypes: string[],
    otherDatatypes: string[]
) {
    for (const t in inputDatatypes) {
        const thisDatatype = inputDatatypes[t]!;

        if (thisDatatype === "input") {
            return new ConnectionAcceptable(true, null);
        }

        // FIXME: No idea what to do about case when datatype is 'input'
        const validMatch = otherDatatypes.some(
            (otherDatatype) =>
                otherDatatype === "input" ||
                otherDatatype === "_sniff_" ||
                datatypesMapper.isSubType(otherDatatype, thisDatatype)
        );

        if (validMatch) {
            return new ConnectionAcceptable(true, null);
        }
    }
    const datatypesSet = new Set(datatypesMapper.datatypes);
    const invalidDatatypes = otherDatatypes.filter((datatype) => !datatypesSet.has(datatype));
    if (invalidDatatypes.length) {
        return new ConnectionAcceptable(
            false,
            `Effective output data type(s) [${invalidDatatypes.join(
                ", "
            )}] unknown. This tool cannot be run on this Galaxy Server at this moment, please contact the Administrator.`
        );
    }
    return new ConnectionAcceptable(
        false,
        `Effective output data type(s) [${otherDatatypes.join(
            ", "
        )}] do not appear to match input type(s) [${inputDatatypes.join(", ")}].`
    );
}

type TerminalSourceAndInvalid = TerminalSource | InvalidOutputTerminalArgs | InvalidInputTerminalArgs;

function isInvalidOutputArg(arg: TerminalSourceAndInvalid): arg is InvalidOutputTerminalArgs {
    return "name" in arg && "valid" in arg && arg.valid === false;
}

function isOutputParameterArg(arg: TerminalSourceAndInvalid): arg is ParameterOutput {
    return "name" in arg && "parameter" in arg && arg.parameter === true;
}

function isOutputCollectionArg(arg: TerminalSourceAndInvalid): arg is CollectionOutput {
    return "name" in arg && "collection" in arg && arg.collection;
}

function isOutputArg(arg: TerminalSourceAndInvalid): arg is DataOutput {
    return "name" in arg && "extensions" in arg;
}

type TerminalOf<T extends TerminalSourceAndInvalid> = T extends InvalidInputTerminalArgs
    ? InvalidInputTerminal
    : T extends DataStepInput
    ? InputTerminal
    : T extends DataCollectionStepInput
    ? InputCollectionTerminal
    : T extends ParameterStepInput
    ? InputParameterTerminal
    : T extends DataOutput
    ? OutputTerminal
    : T extends CollectionOutput
    ? OutputCollectionTerminal
    : T extends ParameterOutput
    ? OutputParameterTerminal
    : T extends BaseOutputTerminalArgs
    ? InvalidOutputTerminal
    : never;

export function terminalFactory<T extends TerminalSourceAndInvalid>(
    stepId: number,
    terminalSource: T,
    datatypesMapper: DatatypesMapperModel,
    stores: ReturnType<typeof useWorkflowStores>
): TerminalOf<T> {
    if ("input_type" in terminalSource) {
        const terminalArgs = {
            datatypesMapper: datatypesMapper,
            input_type: terminalSource.input_type,
            name: terminalSource.name,
            stepId: stepId,
            stores,
        };
        if ("valid" in terminalSource) {
            return new InvalidInputTerminal({
                ...terminalArgs,
                input: {
                    datatypes: [],
                    multiple: false,
                    optional: false,
                },
                valid: terminalSource.valid as false,
            }) as TerminalOf<T>;
        } else {
            const inputArgs = {
                datatypes: terminalSource.extensions,
                multiple: terminalSource.multiple,
                optional: terminalSource.optional,
            };
            if (terminalSource.input_type == "dataset") {
                // type cast appears to be necessary: https://github.com/Microsoft/TypeScript/issues/13995
                return new InputTerminal({
                    ...terminalArgs,
                    input: inputArgs,
                }) as TerminalOf<T>;
            } else if (terminalSource.input_type === "dataset_collection") {
                return new InputCollectionTerminal({
                    ...terminalArgs,
                    collection_types: terminalSource.collection_types,
                    input: {
                        ...inputArgs,
                    },
                }) as TerminalOf<T>;
            } else if (terminalSource.input_type === "parameter") {
                return new InputParameterTerminal({
                    ...terminalArgs,
                    type: terminalSource.type,
                    input: {
                        ...inputArgs,
                    },
                }) as TerminalOf<T>;
            }
        }
    } else if (terminalSource.name) {
        const outputArgs = {
            name: terminalSource.name,
            optional: terminalSource.optional,
            stepId: stepId,
            datatypesMapper: datatypesMapper,
            stores,
        };
        if (isOutputParameterArg(terminalSource)) {
            return new OutputParameterTerminal({
                ...outputArgs,
                multiple: terminalSource.multiple,
                type: terminalSource.type,
            }) as TerminalOf<T>;
        } else if (isOutputCollectionArg(terminalSource)) {
            return new OutputCollectionTerminal({
                ...outputArgs,
                datatypes: terminalSource.extensions,
                collection_type: terminalSource.collection_type,
                collection_type_source: terminalSource.collection_type_source,
            }) as TerminalOf<T>;
        } else if (isOutputArg(terminalSource)) {
            return new OutputTerminal({
                ...outputArgs,
                datatypes: terminalSource.extensions,
            }) as TerminalOf<T>;
        }
    }
    if (isInvalidOutputArg(terminalSource)) {
        return new InvalidOutputTerminal(terminalSource) as TerminalOf<T>;
    }
    throw Error(`Could not build terminal for ${terminalSource}`);
}
