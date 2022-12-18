import { useConnectionStore } from "@/stores/workflowConnectionStore";
import type { Connection } from "@/stores/workflowConnectionStore";
import EventEmitter from "events";
import {
    NULL_COLLECTION_TYPE_DESCRIPTION,
    ANY_COLLECTION_TYPE_DESCRIPTION,
    CollectionTypeDescription,
    type CollectionTypeDescriptor,
} from "./collectionTypeDescription";
import { useWorkflowStepStore } from "@/stores/workflowStepStore";
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
    type: "input" | "output";
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
    type: "input" | "output";

    constructor(attr: BaseTerminalArgs) {
        super();
        this.connectionStore = useConnectionStore();
        this.stepStore = useWorkflowStepStore();
        this.stepId = attr.stepId;
        this.type = attr.type;
        this.name = attr.name;
        this.attributes = attr;
        this.multiple = false;
    }
    public get id() {
        return `node-${this.stepId}-${this.type}-${this.name}`;
    }
    public get connections(): Connection[] {
        return this.connectionStore.getConnectionsForTerminal(this.id);
    }
    public get mapOver(): CollectionTypeDescriptor | null {
        // Make getter ?
        return this.stepStore.stepMapOver[this.stepId] || null;
    }
    connect(connection: Connection) {
        this.connectionStore.addConnection(connection);
    }
    disconnect(connection: Connection) {
        this.connectionStore.removeConnection(connection.id);
        this.resetMappingIfNeeded();
    }
    destroyInvalidConnections() {
        // this.connectors.forEach((connector) => {
        //     if (connector) {
        //         connector.destroyIfInvalid();
        //     }
        // });
        // this.emit("change");
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
        if (!this.mapOver?.equal(outputVal)) {
            this.stepStore.changeStepMapOver(this.stepId, outputVal);
            // TODO: do we even need to listen for this?
            this.emit("changeMapOver", outputVal);
        }
    }
    isMappedOver(): boolean {
        return Boolean(this.mapOver?.isCollection);
    }
    resetMapping() {
        this.stepStore.changeStepMapOver(this.stepId, NULL_COLLECTION_TYPE_DESCRIPTION);
        // necessary ?
        this.emit("changeMapOver", this.mapOver);
    }
    resetCollectionTypeSource() {
        // used to be called on disconnect
        // const node = this.node;
        // Object.values(node.outputTerminals).forEach((output_terminal) => {
        //     const type_source = output_terminal.attributes.collection_type_source;
        //     if (type_source && output_terminal.attributes.collection_type) {
        //         output_terminal.attributes.collection_type = null;
        //         output_terminal.update(output_terminal.attributes);
        //     }
        // });
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
        this.update(attr.input); // subclasses should implement this...
        this.datatypes = attr.input.datatypes;
        this.multiple = attr.input.multiple;
        this.optional = attr.input.optional;
    }
    update(inputData: InputTerminalInputs) {
        this.datatypes = inputData.datatypes;
        this.multiple = inputData.multiple;
        this.optional = inputData.optional;
    }
    // TODO: Do I still need this?
    // setDefaultMapOver(connector) {
    //     var other_output = connector.outputHandle;
    //     if (other_output) {
    //         var otherCollectionType = this._otherCollectionType(other_output);
    //         if (otherCollectionType.isCollection) {
    //             this.setMapOver(otherCollectionType);
    //         }
    //     }
    // }
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
            firstOutput.extensions.indexOf("input") > 0
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

    update(input: InputTerminalInputs) {
        this.datatypes = input.datatypes;
        this.multiple = input.multiple;
        this.optional = input.optional;
        this.collection = false;
    }
    connect(connection: Connection) {
        super.connect(connection);
        // this.setDefaultMapOver(connector);
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
    type: "input";
}

interface ParameterTerminalInputs extends InputTerminalInputs {
    type: "input";
}

export class InputParameterTerminal extends BaseInputTerminal {
    type: "input";

    constructor(attr: InputParameterTerminalArgs) {
        super(attr);
        this.type = attr.type;
    }

    update(input: ParameterTerminalInputs) {
        this.type = input.type;
        this.optional = input.optional;
    }
    connect(connection: Connection) {
        super.connect(connection);
        // this.setDefaultMapOver(connector);
    }
    effectiveType(parameterType: string) {
        return parameterType == "select" ? "text" : parameterType;
    }
    attachable(other: OutputTerminal) {
        const effectiveThisType = this.effectiveType(this.type);
        const effectiveOtherType = this.effectiveType(other.attributes.type);
        return new ConnectionAcceptable(effectiveThisType == effectiveOtherType, "");
    }
}

interface InputCollectionTerminalArgs extends InputTerminalArgs {
    collection_types: string[];
}

export class InputCollectionTerminal extends BaseInputTerminal {
    collection: boolean;
    collectionTypes: CollectionTypeDescriptor[];

    constructor(attr: InputCollectionTerminalArgs) {
        super(attr);
        this.multiple = false;
        this.collection = true;
        this.collectionTypes = attr.collection_types.map(
            (collectionType) => new CollectionTypeDescription(collectionType)
        );
        if (!this.collectionTypes.length) {
            this.collectionTypes.push(ANY_COLLECTION_TYPE_DESCRIPTION);
        }
    }

    // idk, we shouldn't need this I think?
    // update(input) {
    //     this.multiple = false;
    //     this.collection = true;
    //     this.datatypes = input.datatypes;
    //     this.optional = input.optional;
    //     var collectionTypes = [];
    //     if (input.collection_types) {
    //         input.collection_types.forEach((collectionType) => {
    //             );
    //         });
    //     } else {
    //
    //     }
    //     this.collectionTypes = collectionTypes;
    // }
    // TODO: port or drop this, not sure what exactly this is doing, may be covered by mapOver getter?
    connect(connection: Connection) {
        super.connect(connection);
        // var other = connector.outputHandle;
        // if (other) {
        //     const node = this.node;
        //     Object.values(node.outputTerminals).forEach((output_terminal) => {
        //         if (output_terminal.attributes.collection_type_source && !connector.dragging) {
        //             if (other.isMappedOver()) {
        //                 if (other.isCollection) {
        //                     output_terminal.attributes.collection_type = other.mapOver.append(
        //                         other.collectionType
        //                     ).collectionType;
        //                 } else {
        //                     output_terminal.attributes.collection_type = other.mapOver.collectionType;
        //                 }
        //             } else {
        //                 output_terminal.attributes.collection_type = other.attributes.collection_type;
        //             }
        //             output_terminal.update(output_terminal.attributes);
        //         }
        //     });
        // }

        // const effectiveMapOver = this._effectiveMapOver(other);
        // if (effectiveMapOver) {
        //     this.setMapOver(effectiveMapOver);
        // }
    }
    _effectiveMapOver(other: BaseOutputTerminal) {
        const collectionTypes = this.collectionTypes;
        const otherCollectionType = this._otherCollectionType(other);
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
                const effectiveMapOver = this._effectiveMapOver(other);
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

    constructor(attr: BaseOutputTerminalArgs) {
        super(attr);
        this.datatypes = attr.datatypes;
        this.optional = attr.optional;
    }
    // update(output) {
    //     this.extensions = output.datatypes || output.extensions;
    //     this.optional = output.optional;
    // }
}

export class OutputTerminal extends BaseOutputTerminal {
    resetMappingIfNeeded() {
        // TODO: redo this if really needed
        // // If inputs were only mapped over to preserve
        // // an output just disconnected reset these...
        // if (!this.hasConnectedOutputTerminals() && !this.hasConnectedMappedInputTerminals()) {
        //     const node = this.node;
        //     Object.values(node.inputTerminals).forEach((t) => {
        //         if (t.mapOver.isCollection) {
        //             t.resetMappingIfNeeded();
        //         }
        //     });
        // }
        // var noMappedInputs = !this.hasMappedOverInputTerminals();
        // if (noMappedInputs) {
        //     this.resetMapping();
        // }
    }
    resetMapping() {
        super.resetMapping();
        // this.connectors.forEach((connector) => {
        //     var connectedInput = connector.inputHandle;
        //     if (connectedInput) {
        //         // Not exactly right because this is still connected.
        //         // Either rewrite resetMappingIfNeeded or disconnect
        //         // and reconnect if valid.
        //         connectedInput.resetMappingIfNeeded();
        //         connector.destroyIfInvalid();
        //     }
        // });
    }
}

interface OutputCollectionTerminalArgs extends BaseOutputTerminalArgs {
    collection_type: string;
    collection_type_source?: string;
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
    // update(output) {
    //     super.update(output);
    //     var newCollectionType;
    //     if (output.collection_type) {
    //         newCollectionType = new CollectionTypeDescription(output.collection_type);
    //     } else {
    //         var collectionTypeSource = output.collection_type_source;
    //         if (!collectionTypeSource) {
    //             console.log("Warning: No collection type or collection type source defined.");
    //         }
    //         newCollectionType = ANY_COLLECTION_TYPE_DESCRIPTION;
    //     }
    //     const oldCollectionType = this.collectionType;
    //     this.collectionType = newCollectionType;
    //     // we need to iterate over a copy, as we slice this.connectors in the process of destroying connections
    //     var connectors = this.connectors.slice(0);
    //     if (newCollectionType.collectionType != oldCollectionType.collectionType) {
    //         connectors.forEach((connector) => {
    //             connector.destroyIfInvalid(true);
    //         });
    //     }
    // }
}

interface OutputParameterTerminalArgs extends Omit<BaseOutputTerminalArgs, "type"> {
    // TODO: type is parameter type (text, integer etc)
    type: string;
}

export class OutputParameterTerminal extends Terminal {
    update(output: OutputParameterTerminalArgs) {
        this.attributes.type = output.type;
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
