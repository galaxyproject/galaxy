import { useConnectionStore } from "@/stores/workflowConnectionStore";
import { Connection } from "@/stores/workflowConnectionStore";
import EventEmitter from "events";
import {
    NULL_COLLECTION_TYPE_DESCRIPTION,
    ANY_COLLECTION_TYPE_DESCRIPTION,
    CollectionTypeDescription,
    type CollectionTypeDescriptor,
} from "./collectionTypeDescription";
import { useWorkflowStepStore } from "@/stores/workflowStepStore";
import type {
    DataStepInput,
    DataOutput,
    CollectionOutput,
    ParameterOutput,
    DataCollectionStepInput,
    ParameterStepInput,
} from "@/stores/workflowStepStore";
import type { DatatypesMapperModel } from "@/components/Datatypes/model";

class ConnectionAcceptable {
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
}

interface InputTerminalInputs {
    datatypes: string[];
    multiple: boolean;
    optional: boolean;
}

interface InputTerminalArgs extends BaseTerminalArgs {
    datatypesMapper: DatatypesMapperModel;
    input: InputTerminalInputs;
}

class Terminal extends EventEmitter {
    connectionStore: ReturnType<typeof useConnectionStore>;
    stepStore: ReturnType<typeof useWorkflowStepStore>;
    name: string;
    // TODO: get rid of all any's
    attributes: any;
    multiple: boolean;
    stepId: number;
    terminalType: "input" | "output";

    constructor(attr: BaseTerminalArgs) {
        super();
        this.connectionStore = useConnectionStore();
        this.stepStore = useWorkflowStepStore();
        this.stepId = attr.stepId;
        this.name = attr.name;
        this.attributes = attr;
        this.multiple = false;
        this.terminalType = "input";
    }
    public get id() {
        return `node-${this.stepId}-${this.terminalType}-${this.name}`;
    }
    public get connections(): Connection[] {
        return this.connectionStore.getConnectionsForTerminal(this.id);
    }
    public get mapOver(): CollectionTypeDescriptor {
        return this.stepStore.stepMapOver[this.stepId] || NULL_COLLECTION_TYPE_DESCRIPTION;
    }
    connect(other: Terminal) {
        const connection = new Connection(
            { stepId: this.stepId, name: this.name, connectorType: "input" },
            { stepId: other.stepId, name: other.name, connectorType: "output" }
        );
        this.connectionStore.addConnection(connection);
    }
    disconnect(other: Terminal) {
        const connection = new Connection(
            { stepId: this.stepId, name: this.name, connectorType: "input" },
            { stepId: other.stepId, name: other.name, connectorType: "output" }
        );
        this.connectionStore.removeConnection(connection.id);
        this.resetMappingIfNeeded();
    }
    setMapOver(val: CollectionTypeDescriptor) {
        let outputVal = val;
        if (this.multiple) {
            // emulate list input
            const description = new CollectionTypeDescription("list");
            if (val.collectionType === description.collectionType) {
                // No mapping over necessary
                return;
            }
            outputVal = val.effectiveMapOver(description) || val;
        }
        const effectiveMapOver = this._effectiveMapOver(outputVal);
        if (!this.mapOver.equal(effectiveMapOver)) {
            this.stepStore.changeStepMapOver(this.stepId, effectiveMapOver);
            // TODO: do we even need to listen for this?
            this.emit("changeMapOver", outputVal);
        }
    }
    _effectiveMapOver(otherCollectionType: CollectionTypeDescriptor) {
        return otherCollectionType;
    }
    isMappedOver(): boolean {
        return Boolean(this.mapOver?.isCollection);
    }
    resetMapping() {
        this.stepStore.changeStepMapOver(this.stepId, NULL_COLLECTION_TYPE_DESCRIPTION);
        // necessary ?
        this.emit("changeMapOver", this.mapOver);
    }
    hasConnectedMappedInputTerminals() {
        // check if step has connected and mapped input terminals ... should maybe be on step/node ?
        const connections = this.connectionStore.getConnectionsForStep(this.stepId);
        return connections.some(
            (connection) =>
                connection.input.stepId === this.stepId && this.stepStore.stepMapOver[this.stepId]?.collectionType
        );
    }
    hasConnectedOutputTerminals() {
        // Does this step/node have connected connections
        const connections = this.connectionStore.getConnectionsForStep(this.stepId);
        return connections.some((connection) => connection.output.stepId === this.stepId);
    }
    hasMappedOverInputTerminals() {
        return Boolean(this.stepStore.stepMapOver[this.stepId]?.collectionType);
    }
    // Subclasses should override this...
    resetMappingIfNeeded() {}
}

class BaseInputTerminal extends Terminal {
    datatypesMapper: DatatypesMapperModel;
    datatypes: InputTerminalInputs["datatypes"];
    optional: InputTerminalInputs["optional"];

    constructor(attr: InputTerminalArgs) {
        super(attr);
        this.datatypesMapper = attr.datatypesMapper;
        this.datatypes = attr.input.datatypes;
        this.multiple = attr.input.multiple;
        this.optional = attr.input.optional;
    }
    connect(other: BaseOutputTerminal): void {
        super.connect(other);
        this.setDefaultMapOver(other);
    }
    // TODO: Do I still need this?
    setDefaultMapOver(other: BaseOutputTerminal) {
        const otherCollectionType = this._otherCollectionType(other);
        if (otherCollectionType.isCollection) {
            this.setMapOver(otherCollectionType);
        }
    }
    canAccept(outputTerminal: BaseOutputTerminal) {
        if (this._inputFilled()) {
            return new ConnectionAcceptable(
                false,
                "Input already filled with another connection, delete it before connecting another output."
            );
        } else {
            return this.attachable(outputTerminal);
        }
    }
    attachable(terminal: BaseOutputTerminal): ConnectionAcceptable {
        throw "Subclass needs to implement this";
    }
    resetMappingIfNeeded() {
        const mapOver = this.mapOver;
        if (!mapOver?.isCollection) {
            return;
        }
        // No output terminals are counting on this being mapped
        // over if connected inputs are still mapped over or if none
        // of the outputs are connected...
        const reset = this.hasConnectedMappedInputTerminals() || !this.hasConnectedOutputTerminals();
        if (reset) {
            this.resetMapping();
        }
    }
    resetMapping() {
        super.resetMapping();
        // TODO: still needed?
        // if (!this.hasMappedOverInputTerminals()) {
        //     Object.values(this.node.outputTerminals).forEach((terminal) => {
        //         // This shouldn't be called if there are mapped over
        //         // outputs.
        //         terminal.resetMapping();
        //     });
        // }
    }
    getFirstOutputTerminal() {
        const outputTerminals = this.connectionStore.getOutputTerminalsForInputTerminal(this.id);
        if (outputTerminals.length > 0) {
            return outputTerminals[0];
        }
        return null;
    }
    connected() {
        return Boolean(this.getFirstOutputTerminal());
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
        if (!this.connected()) {
            return false;
        }
        const firstOutputTerminal = this.getFirstOutputTerminal();
        if (!firstOutputTerminal) {
            return false;
        }
        const firstOutput = this.stepStore
            .getStep(firstOutputTerminal.stepId)
            .outputs.find((output) => output.name == firstOutputTerminal.name);
        if (!firstOutput) {
            return false;
        }
        if (
            ("collection" in firstOutput && firstOutput.collection) ||
            this.stepStore.stepMapOver[firstOutputTerminal.stepId]?.isCollection ||
            ("extensions" in firstOutput && firstOutput.extensions.indexOf("input") > 0)
        ) {
            return true;
        } else {
            return false;
        }
    }
    _mappingConstraints() {
        // If this is a connected terminal, return list of collection types
        // other terminals connected to node are constraining mapping to.
        // Marius: how can you have a terminal that is not attached to a node? Dragging terminal ?
        // const node = this.node;
        // if (!node) {
        //     return []; // No node - completely unconstrained
        // }
        const mapOver = this.mapOver;
        if (mapOver?.isCollection) {
            return [mapOver];
        }
        // this check seems unnecessary, this.mapOver should reflect the mapOver constraint already
        //const constraints = [];
        // if (!this.hasConnectedOutputTerminals()) {
        //     Object.values(node.inputTerminals).forEach((t) => {
        //         const mapOver = t.mapOver;
        //         if (mapOver.isCollection) {
        //             if (t.connectors.length > 0) {
        //                 constraints.push(t.mapOver);
        //             }
        //         }
        //     });
        // }
        // All outputs should have same mapOver status - least specific.
        const firstOutputTerminal = this.getFirstOutputTerminal();
        if (firstOutputTerminal && this.stepStore.stepMapOver[firstOutputTerminal.stepId]) {
            return [this.stepStore.stepMapOver[firstOutputTerminal.stepId]];
        }
        return [];
    }
    _producesAcceptableDatatype(other: BaseOutputTerminal) {
        // other is a non-collection output...

        if (other instanceof OutputParameterTerminal) {
            return new ConnectionAcceptable(false, "Cannot connect workflow parameter to data input.");
        }

        return producesAcceptableDatatype(this.datatypesMapper, this.datatypes, other.datatypes);
    }
    _isSubType(child: string, parent: string) {
        return this.datatypesMapper.isSubType(child, parent);
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
        if (otherMapOver?.isCollection) {
            otherCollectionType = otherMapOver.append(otherCollectionType);
        }
        return otherCollectionType;
    }
}

export class InputTerminal extends BaseInputTerminal {
    collection: boolean;

    constructor(attr: InputTerminalArgs) {
        super(attr);
        this.collection = false;
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
            if (mapOver?.isCollection && mapOver.canMatch(otherCollectionType)) {
                return this._producesAcceptableDatatypeAndOptionalness(other);
            } else if (this.multiple && new CollectionTypeDescription("list").canMatch(otherCollectionType)) {
                // This handles the special case of a list input being connected to a multiple="true" data input.
                // Nested lists would be correctly mapped over by the above condition.
                return this._producesAcceptableDatatypeAndOptionalness(other);
            } else {
                //  Need to check if this would break constraints...
                const mappingConstraints = this._mappingConstraints();
                if (mappingConstraints.every(otherCollectionType.canMatch.bind(otherCollectionType))) {
                    return this._producesAcceptableDatatypeAndOptionalness(other);
                } else {
                    if (mapOver?.isCollection) {
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
                            "Can't map over this input with output collection type - an output of this tool is not mapped over constraining this input. Disconnect output(s) and retry."
                        );
                    }
                }
            }
        } else if (mapOver?.isCollection) {
            return new ConnectionAcceptable(
                false,
                "Cannot attach non-collection outputs to mapped over inputs, consider disconnecting inputs and outputs to reset this input's mapping."
            );
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
    }

    effectiveType(parameterType: string) {
        return parameterType == "select" ? "text" : parameterType;
    }
    attachable(other: BaseOutputTerminal) {
        const effectiveThisType = this.effectiveType(this.type);
        const otherType = ("type" in other && other.type) || "data";
        const effectiveOtherType = this.effectiveType(otherType);
        return new ConnectionAcceptable(
            effectiveThisType == effectiveOtherType,
            `Cannot attach a ${effectiveOtherType} parameter to a ${effectiveThisType} input`
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
    }

    // TODO: port or drop this, not sure what exactly this is doing, may be covered by mapOver getter?
    // connect(other) {
    //     super.connect(other);
    //     // var other = connector.outputHandle;
    //     // if (other) {
    //     //     const node = this.node;
    //     //     Object.values(node.outputTerminals).forEach((output_terminal) => {
    //     //         if (output_terminal.attributes.collection_type_source && !connector.dragging) {
    //     //             if (other.isMappedOver()) {
    //     //                 if (other.isCollection) {
    //     //                     output_terminal.attributes.collection_type = other.mapOver.append(
    //     //                         other.collectionType
    //     //                     ).collectionType;
    //     //                 } else {
    //     //                     output_terminal.attributes.collection_type = other.mapOver.collectionType;
    //     //                 }
    //     //             } else {
    //     //                 output_terminal.attributes.collection_type = other.attributes.collection_type;
    //     //             }
    //     //             output_terminal.update(output_terminal.attributes);
    //     //         }
    //     //     });
    //     // }

    //     // const effectiveMapOver = this._effectiveMapOver(other);
    //     // if (effectiveMapOver) {
    //     //     this.setMapOver(effectiveMapOver);
    //     // }
    // }
    _effectiveMapOver(otherCollectionType: CollectionTypeDescriptor) {
        const collectionTypes = this.collectionTypes;
        const canMatch = collectionTypes.some((collectionType) => collectionType.canMatch(otherCollectionType));
        if (!canMatch) {
            for (const collectionTypeIndex in collectionTypes) {
                const collectionType = collectionTypes[collectionTypeIndex];
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
        const mapOver = this.mapOver;
        return this.collectionTypes.map((t) => mapOver?.append(t));
    }
    attachable(other: BaseOutputTerminal) {
        const otherCollectionType = this._otherCollectionType(other);
        if (otherCollectionType.isCollection) {
            const effectiveCollectionTypes = this._effectiveCollectionTypes();
            const mapOver = this.mapOver;
            const canMatch = effectiveCollectionTypes.some((effectiveCollectionType) =>
                effectiveCollectionType?.canMatch(otherCollectionType)
            );
            if (canMatch) {
                // Only way a direct match...
                return this._producesAcceptableDatatypeAndOptionalness(other);
                // Otherwise we need to mapOver
            } else if (mapOver?.isCollection) {
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
                if (!effectiveMapOver?.isCollection) {
                    return new ConnectionAcceptable(false, "Incompatible collection type(s) for attachment.");
                }
                //  Need to check if this would break constraints...
                const mappingConstraints = this._mappingConstraints();
                if (mappingConstraints.every((d) => effectiveMapOver.canMatch(d))) {
                    return this._producesAcceptableDatatypeAndOptionalness(other);
                } else {
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

class BaseOutputTerminal extends Terminal {
    datatypes: BaseOutputTerminalArgs["datatypes"];
    optional: BaseOutputTerminalArgs["optional"];
    isCollection?: boolean;
    collectionType?: CollectionTypeDescriptor;
    type?: string;

    constructor(attr: BaseOutputTerminalArgs) {
        super(attr);
        this.datatypes = attr.datatypes;
        this.optional = attr.optional;
        this.terminalType = "output";
    }
}

export class OutputTerminal extends BaseOutputTerminal {}

interface OutputCollectionTerminalArgs extends BaseOutputTerminalArgs {
    collection_type: string;
    collection_type_source: string | null;
}

export class OutputCollectionTerminal extends BaseOutputTerminal {
    constructor(attr: OutputCollectionTerminalArgs) {
        super(attr);
        if (attr.collection_type) {
            this.collectionType = new CollectionTypeDescription(attr.collection_type);
        } else {
            const collectionTypeSource = attr.collection_type_source;
            if (!collectionTypeSource) {
                console.log("Warning: No collection type or collection type source defined.");
            }
            this.collectionType = ANY_COLLECTION_TYPE_DESCRIPTION;
        }
        this.isCollection = true;
    }
}

interface OutputParameterTerminalArgs extends Omit<BaseOutputTerminalArgs, "datatypes"> {
    // TODO: type is parameter type (text, integer etc)
    type: ParameterOutput["type"];
}

export class OutputParameterTerminal extends Terminal {
    constructor(attr: OutputParameterTerminalArgs) {
        super(attr);
    }
}

export function producesAcceptableDatatype(
    datatypesMapper: DatatypesMapperModel,
    inputDatatypes: string[],
    otherDatatypes: string[]
) {
    for (const t in inputDatatypes) {
        const thisDatatype = inputDatatypes[t];
        if (thisDatatype == "input") {
            return new ConnectionAcceptable(true, null);
        }
        // FIXME: No idea what to do about case when datatype is 'input'
        const validMatch = otherDatatypes.some(
            (otherDatatype) =>
                otherDatatype == "input" ||
                otherDatatype == "_sniff_" ||
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

type TerminalOf<T> = T extends DataStepInput
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
    : never;

export function terminalFactory(
    stepId: number,
    terminalSource:
        | DataStepInput
        | DataCollectionStepInput
        | ParameterStepInput
        | DataOutput
        | CollectionOutput
        | ParameterOutput,
    datatypesMapper: DatatypesMapperModel
): TerminalOf<typeof terminalSource> {
    if ("input_type" in terminalSource) {
        const terminalArgs = {
            datatypesMapper: datatypesMapper,
            name: terminalSource.name,
            stepId: stepId,
        };
        const inputArgs = {
            datatypes: terminalSource.extensions,
            multiple: terminalSource.multiple,
            optional: terminalSource.optional,
        };
        if (terminalSource.input_type === "dataset") {
            return new InputTerminal({
                ...terminalArgs,
                input: inputArgs,
            });
        } else if (terminalSource.input_type === "dataset_collection") {
            return new InputCollectionTerminal({
                ...terminalArgs,
                collection_types: terminalSource.collection_types,
                input: {
                    ...inputArgs,
                },
            });
        } else if (terminalSource.input_type === "parameter") {
            return new InputParameterTerminal({
                ...terminalArgs,
                type: terminalSource.type,
                input: {
                    ...inputArgs,
                },
            });
        }
    } else {
        const outputArgs = {
            name: terminalSource.name,
            optional: terminalSource.optional,
            stepId: stepId,
        };
        if ("parameter" in terminalSource) {
            return new OutputParameterTerminal({
                ...outputArgs,
                type: terminalSource.type,
            });
        } else if ("collection" in terminalSource && terminalSource.collection) {
            return new OutputCollectionTerminal({
                ...outputArgs,
                datatypes: terminalSource.extensions,
                collection_type: terminalSource.collection_type,
                collection_type_source: terminalSource.collection_type_source,
            });
        } else {
            return new OutputTerminal({
                ...outputArgs,
                datatypes: terminalSource.extensions,
            });
        }
    }
    throw `Could not build terminal for ${terminalSource}`;
}
