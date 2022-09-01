import EventEmitter from "events";

const NULL_COLLECTION_TYPE_DESCRIPTION = {
    isCollection: false,
    canMatch: function () {
        return false;
    },
    canMapOver: function () {
        return false;
    },
    toString: function () {
        return "NullCollectionType[]";
    },
    append: function (otherCollectionType) {
        return otherCollectionType;
    },
    equal: function (other) {
        return other === this;
    },
};

const ANY_COLLECTION_TYPE_DESCRIPTION = {
    isCollection: true,
    canMatch: function (other) {
        return NULL_COLLECTION_TYPE_DESCRIPTION !== other;
    },
    canMapOver: function () {
        return false;
    },
    toString: function () {
        return "AnyCollectionType[]";
    },
    append: function () {
        return ANY_COLLECTION_TYPE_DESCRIPTION;
    },
    equal: function (other) {
        return other === this;
    },
};

class ConnectionAcceptable {
    constructor(canAccept, reason) {
        this.canAccept = canAccept;
        this.reason = reason;
    }
}

class CollectionTypeDescription {
    constructor(collectionType) {
        this.collectionType = collectionType;
        this.isCollection = true;
        this.rank = collectionType.split(":").length;
    }
    append(otherCollectionTypeDescription) {
        if (otherCollectionTypeDescription === NULL_COLLECTION_TYPE_DESCRIPTION) {
            return this;
        }
        if (otherCollectionTypeDescription === ANY_COLLECTION_TYPE_DESCRIPTION) {
            return otherCollectionTypeDescription;
        }
        return new CollectionTypeDescription(`${this.collectionType}:${otherCollectionTypeDescription.collectionType}`);
    }
    canMatch(otherCollectionTypeDescription) {
        if (otherCollectionTypeDescription === NULL_COLLECTION_TYPE_DESCRIPTION) {
            return false;
        }
        if (otherCollectionTypeDescription === ANY_COLLECTION_TYPE_DESCRIPTION) {
            return true;
        }
        return otherCollectionTypeDescription.collectionType == this.collectionType;
    }
    canMapOver(otherCollectionTypeDescription) {
        if (otherCollectionTypeDescription === NULL_COLLECTION_TYPE_DESCRIPTION) {
            return false;
        }
        if (otherCollectionTypeDescription === ANY_COLLECTION_TYPE_DESCRIPTION) {
            return false;
        }
        if (this.rank <= otherCollectionTypeDescription.rank) {
            // Cannot map over self...
            return false;
        }
        var requiredSuffix = otherCollectionTypeDescription.collectionType;
        return this._endsWith(this.collectionType, requiredSuffix);
    }
    effectiveMapOver(otherCollectionTypeDescription) {
        var otherCollectionType = otherCollectionTypeDescription.collectionType;
        var effectiveCollectionType = this.collectionType.substring(
            0,
            this.collectionType.length - otherCollectionType.length - 1
        );
        return new CollectionTypeDescription(effectiveCollectionType);
    }
    equal(otherCollectionTypeDescription) {
        return otherCollectionTypeDescription.collectionType == this.collectionType;
    }
    toString() {
        return `CollectionType[${this.collectionType}]`;
    }
    _endsWith(str, suffix) {
        return str.indexOf(suffix, str.length - suffix.length) !== -1;
    }
}

class Terminal extends EventEmitter {
    constructor(attr) {
        super();
        this.name = attr.name;
        this.node = attr.node;
        this.element = attr.element;
        this.mapOver = attr.mapOver || NULL_COLLECTION_TYPE_DESCRIPTION;
        this.attributes = attr;
        this.connectors = [];
    }
    connect(connector) {
        this.connectors.push(connector);
        this.emit("change");
    }
    disconnect(connector) {
        const connectorIndex = this.connectors.findIndex((c) => c === connector);
        this.connectors.splice(connectorIndex, 1);
        this.resetMappingIfNeeded();
        if (!connector.dragging) {
            connector.inputHandle.resetCollectionTypeSource();
        }
        this.emit("change");
    }
    redraw() {
        this.connectors.forEach((c) => {
            c.redraw();
        });
    }
    destroy() {
        this.connectors.slice().forEach((c) => {
            c.destroy();
        });
        this.emit("change");
    }
    destroyInvalidConnections() {
        this.connectors.forEach((connector) => {
            if (connector) {
                connector.destroyIfInvalid();
            }
        });
        this.emit("change");
    }
    setMapOver(val) {
        let output_val = val;
        if (this.multiple) {
            // emulate list input
            const description = new CollectionTypeDescription("list");
            if (val.collectionType === description.collectionType) {
                // No mapping over necessary
                return;
            }
            output_val = val.effectiveMapOver ? val.effectiveMapOver(description) : val;
        }
        if (!this.mapOver.equal(val)) {
            this.mapOver = val;
            this.node.mapOver = output_val;
            Object.values(this.node.outputTerminals).forEach((outputTerminal) => {
                outputTerminal.setMapOver(output_val);
            });
        }
        this.emit("change");
    }
    isMappedOver() {
        return this.mapOver.isCollection;
    }
    resetMapping() {
        this.mapOver = NULL_COLLECTION_TYPE_DESCRIPTION;
        this.node.mapOver = undefined;
        this.emit("change");
    }
    resetCollectionTypeSource() {
        const node = this.node;
        Object.values(node.outputTerminals).forEach((output_terminal) => {
            const type_source = output_terminal.attributes.collection_type_source;
            if (type_source && output_terminal.attributes.collection_type) {
                output_terminal.attributes.collection_type = null;
                output_terminal.update(output_terminal.attributes);
            }
        });
    }
    hasConnectedMappedInputTerminals() {
        const node = this.node;
        const inputTerminals = node.inputTerminals;
        for (const inputName in inputTerminals) {
            const inputTerminal = inputTerminals[inputName];
            if (inputTerminal.connectors.length > 0 && inputTerminal.isMappedOver()) {
                return true;
            }
        }
        return false;
    }
    hasConnectedOutputTerminals() {
        const node = this.node;
        const outputTerminals = node.outputTerminals;
        for (const outputName in outputTerminals) {
            if (outputTerminals[outputName].connectors.length > 0) {
                return true;
            }
        }
        return false;
    }
    hasMappedOverInputTerminals() {
        const node = this.node;
        const inputTerminals = node.inputTerminals;
        for (const inputName in inputTerminals) {
            const terminal = inputTerminals[inputName];
            if (terminal.mapOver.isCollection) {
                return true;
            }
        }
        return false;
    }
    // Subclasses should override this...
    resetMappingIfNeeded() {}
}

class BaseInputTerminal extends Terminal {
    constructor(attr) {
        super(attr);
        this.datatypesMapper = attr.datatypesMapper;
        this.update(attr.input); // subclasses should implement this...
    }
    setDefaultMapOver(connector) {
        var other_output = connector.outputHandle;
        if (other_output) {
            var otherCollectionType = this._otherCollectionType(other_output);
            if (otherCollectionType.isCollection) {
                this.setMapOver(otherCollectionType);
            }
        }
    }
    canAccept(other) {
        if (this._inputFilled()) {
            return new ConnectionAcceptable(
                false,
                "Input already filled with another connection, delete it before connecting another output."
            );
        } else {
            return this.attachable(other);
        }
    }
    resetMappingIfNeeded() {
        var mapOver = this.mapOver;
        if (!mapOver.isCollection) {
            return;
        }
        // No output terminals are counting on this being mapped
        // over if connected inputs are still mapped over or if none
        // of the outputs are connected...
        var reset = this.hasConnectedMappedInputTerminals() || !this.hasConnectedOutputTerminals();
        if (reset) {
            this.resetMapping();
        }
    }
    resetMapping() {
        super.resetMapping();
        if (!this.hasMappedOverInputTerminals()) {
            Object.values(this.node.outputTerminals).forEach((terminal) => {
                // This shouldn't be called if there are mapped over
                // outputs.
                terminal.resetMapping();
            });
        }
    }
    connected() {
        return this.connectors.length !== 0;
    }
    _inputFilled() {
        var inputFilled;
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
        } else {
            var firstOutput = this.connectors[0].outputHandle;
            if (!firstOutput) {
                return false;
            } else {
                if (
                    firstOutput.isCollection ||
                    firstOutput.isMappedOver() ||
                    firstOutput.datatypes.indexOf("input") > 0
                ) {
                    return true;
                } else {
                    return false;
                }
            }
        }
    }
    _mappingConstraints() {
        // If this is a connected terminal, return list of collection types
        // other terminals connected to node are constraining mapping to.
        const node = this.node;
        if (!node) {
            return []; // No node - completely unconstrained
        }
        var mapOver = this.mapOver;
        if (mapOver.isCollection) {
            return [mapOver];
        }
        const constraints = [];
        if (!this.hasConnectedOutputTerminals()) {
            Object.values(node.inputTerminals).forEach((t) => {
                const mapOver = t.mapOver;
                if (mapOver.isCollection) {
                    if (t.connectors.length > 0) {
                        constraints.push(t.mapOver);
                    }
                }
            });
        } else {
            // All outputs should have same mapOver status - least specific.
            constraints.push(Object.values(node.outputTerminals)[0].mapOver);
        }
        return constraints;
    }
    _producesAcceptableDatatype(other) {
        // other is a non-collection output...

        if (other instanceof OutputParameterTerminal) {
            return new ConnectionAcceptable(false, "Cannot connect workflow parameter to data input.");
        }

        for (const t in this.datatypes) {
            const thisDatatype = this.datatypes[t];
            if (thisDatatype == "input") {
                return new ConnectionAcceptable(true, null);
            }
            // FIXME: No idea what to do about case when datatype is 'input'
            const validMatch = other.datatypes.some(
                (other_datatype) =>
                    other_datatype == "input" ||
                    other_datatype == "_sniff_" ||
                    this._isSubType(other_datatype, thisDatatype)
            );
            if (validMatch) {
                return new ConnectionAcceptable(true, null);
            }
        }
        const datatypesSet = new Set(this.datatypesMapper.datatypes);
        const invalidDatatypes = other.datatypes.filter((datatype) => !datatypesSet.has(datatype));
        if (invalidDatatypes.length) {
            return new ConnectionAcceptable(
                false,
                `Effective output data type(s) [${invalidDatatypes.join(
                    ", "
                )}] unknown. This tool cannot be executed on this Galaxy Server at this moment, please contact the Administrator.`
            );
        }
        return new ConnectionAcceptable(
            false,
            `Effective output data type(s) [${other.datatypes.join(
                ", "
            )}] do not appear to match input type(s) [${this.datatypes.join(", ")}].`
        );
    }
    _isSubType(child, parent) {
        return this.datatypesMapper.isSubType(child, parent);
    }
    _producesAcceptableDatatypeAndOptionalness(other) {
        if (!this.optional && !this.multiple && other.optional) {
            return new ConnectionAcceptable(false, "Cannot connect an optional output to a non-optional input");
        }
        return this._producesAcceptableDatatype(other);
    }
    _otherCollectionType(other) {
        var otherCollectionType = NULL_COLLECTION_TYPE_DESCRIPTION;
        if (other.isCollection) {
            otherCollectionType = other.collectionType;
        }
        var otherMapOver = other.mapOver;
        if (otherMapOver.isCollection) {
            otherCollectionType = otherMapOver.append(otherCollectionType);
        }
        return otherCollectionType;
    }
}

class InputTerminal extends BaseInputTerminal {
    update(input) {
        this.datatypes = input.extensions;
        this.multiple = input.multiple;
        this.optional = input.optional;
        this.collection = false;
    }
    connect(connector) {
        super.connect(connector);
        this.setDefaultMapOver(connector);
    }
    attachable(other) {
        var otherCollectionType = this._otherCollectionType(other);
        var mapOver = this.mapOver;
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
            } else if (this.multiple && new CollectionTypeDescription("list").canMatch(otherCollectionType)) {
                // This handles the special case of a list input being connected to a multiple="true" data input.
                // Nested lists would be correctly mapped over by the above condition.
                return this._producesAcceptableDatatypeAndOptionalness(other);
            } else {
                //  Need to check if this would break constraints...
                var mappingConstraints = this._mappingConstraints();
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
                            "Can't map over this input with output collection type - an output of this tool is not mapped over constraining this input. Disconnect output(s) and retry."
                        );
                    }
                }
            }
        } else if (mapOver.isCollection) {
            return new ConnectionAcceptable(
                false,
                "Cannot attach non-collection outputs to mapped over inputs, consider disconnecting inputs and outputs to reset this input's mapping."
            );
        }
        return this._producesAcceptableDatatypeAndOptionalness(other);
    }
}

class InputParameterTerminal extends BaseInputTerminal {
    update(input) {
        this.type = input.type;
        this.optional = input.optional;
    }
    connect(connector) {
        super.connect(connector);
        this.setDefaultMapOver(connector);
    }
    effectiveType(parameterType) {
        return parameterType == "select" ? "text" : parameterType;
    }
    attachable(other) {
        const effectiveThisType = this.effectiveType(this.type);
        const effectiveOtherType = this.effectiveType(other.attributes.type);
        return new ConnectionAcceptable(effectiveThisType == effectiveOtherType, "");
    }
}

class InputCollectionTerminal extends BaseInputTerminal {
    update(input) {
        this.multiple = false;
        this.collection = true;
        this.collection_type = input.collection_type;
        this.datatypes = input.extensions;
        this.optional = input.optional;
        var collectionTypes = [];
        if (input.collection_types) {
            input.collection_types.forEach((collectionType) => {
                collectionTypes.push(new CollectionTypeDescription(collectionType));
            });
        } else {
            collectionTypes.push(ANY_COLLECTION_TYPE_DESCRIPTION);
        }
        this.collectionTypes = collectionTypes;
    }
    connect(connector) {
        super.connect(connector);
        var other = connector.outputHandle;
        if (other) {
            const node = this.node;
            Object.values(node.outputTerminals).forEach((output_terminal) => {
                if (output_terminal.attributes.collection_type_source && !connector.dragging) {
                    if (other.isMappedOver()) {
                        if (other.isCollection) {
                            output_terminal.attributes.collection_type = other.mapOver.append(
                                other.collectionType
                            ).collectionType;
                        } else {
                            output_terminal.attributes.collection_type = other.mapOver.collectionType;
                        }
                    } else {
                        output_terminal.attributes.collection_type = other.attributes.collection_type;
                    }
                    output_terminal.update(output_terminal.attributes);
                }
            });
        }

        var effectiveMapOver = this._effectiveMapOver(other);
        this.setMapOver(effectiveMapOver);
    }
    _effectiveMapOver(other) {
        var collectionTypes = this.collectionTypes;
        var otherCollectionType = this._otherCollectionType(other);
        var canMatch = collectionTypes.some((collectionType) => collectionType.canMatch(otherCollectionType));
        if (!canMatch) {
            for (var collectionTypeIndex in collectionTypes) {
                var collectionType = collectionTypes[collectionTypeIndex];
                if (otherCollectionType.canMapOver(collectionType)) {
                    var effectiveMapOver = otherCollectionType.effectiveMapOver(collectionType);
                    if (effectiveMapOver != NULL_COLLECTION_TYPE_DESCRIPTION) {
                        return effectiveMapOver;
                    }
                }
            }
        }
        return NULL_COLLECTION_TYPE_DESCRIPTION;
    }
    _effectiveCollectionTypes() {
        var mapOver = this.mapOver;
        return this.collectionTypes.map((t) => mapOver.append(t));
    }
    attachable(other) {
        var otherCollectionType = this._otherCollectionType(other);
        if (otherCollectionType.isCollection) {
            var effectiveCollectionTypes = this._effectiveCollectionTypes();
            var mapOver = this.mapOver;
            var canMatch = effectiveCollectionTypes.some((effectiveCollectionType) =>
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
                var effectiveMapOver = this._effectiveMapOver(other);
                if (!effectiveMapOver.isCollection) {
                    return new ConnectionAcceptable(false, "Incompatible collection type(s) for attachment.");
                }
                //  Need to check if this would break constraints...
                var mappingConstraints = this._mappingConstraints();
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

class BaseOutputTerminal extends Terminal {
    constructor(attr) {
        super(attr);
        this.datatypes = attr.datatypes;
        this.optional = attr.optional;
        if (this.node.mapOver) {
            this.setMapOver(this.node.mapOver);
        }
    }
    update(output) {
        this.datatypes = output.datatypes || output.extensions;
        this.optional = output.optional;
    }
}

class OutputTerminal extends BaseOutputTerminal {
    resetMappingIfNeeded() {
        // If inputs were only mapped over to preserve
        // an output just disconnected reset these...
        if (!this.hasConnectedOutputTerminals() && !this.hasConnectedMappedInputTerminals()) {
            const node = this.node;
            Object.values(node.inputTerminals).forEach((t) => {
                if (t.mapOver.isCollection) {
                    t.resetMappingIfNeeded();
                }
            });
        }
        var noMappedInputs = !this.hasMappedOverInputTerminals();
        if (noMappedInputs) {
            this.resetMapping();
        }
    }
    resetMapping() {
        super.resetMapping();
        this.connectors.forEach((connector) => {
            var connectedInput = connector.inputHandle;
            if (connectedInput) {
                // Not exactly right because this is still connected.
                // Either rewrite resetMappingIfNeeded or disconnect
                // and reconnect if valid.
                connectedInput.resetMappingIfNeeded();
                connector.destroyIfInvalid();
            }
        });
    }
}

class OutputCollectionTerminal extends BaseOutputTerminal {
    constructor(attr) {
        super(attr);
        if (attr.collection_type) {
            this.collectionType = new CollectionTypeDescription(attr.collection_type);
        } else {
            var collectionTypeSource = attr.collection_type_source;
            if (!collectionTypeSource) {
                console.log("Warning: No collection type or collection type source defined.");
            }
            this.collectionType = ANY_COLLECTION_TYPE_DESCRIPTION;
        }
        this.isCollection = true;
    }
    update(output) {
        super.update(output);
        var newCollectionType;
        if (output.collection_type) {
            newCollectionType = new CollectionTypeDescription(output.collection_type);
        } else {
            var collectionTypeSource = output.collection_type_source;
            if (!collectionTypeSource) {
                console.log("Warning: No collection type or collection type source defined.");
            }
            newCollectionType = ANY_COLLECTION_TYPE_DESCRIPTION;
        }
        const oldCollectionType = this.collectionType;
        this.collectionType = newCollectionType;
        // we need to iterate over a copy, as we slice this.connectors in the process of destroying connections
        var connectors = this.connectors.slice(0);
        if (newCollectionType.collectionType != oldCollectionType.collectionType) {
            connectors.forEach((connector) => {
                connector.destroyIfInvalid(true);
            });
        }
    }
}

class OutputParameterTerminal extends Terminal {
    update(output) {
        this.attributes.type = output.type;
    }
}

export default {
    Terminal: Terminal,
    InputTerminal: InputTerminal,
    InputParameterTerminal: InputParameterTerminal,
    OutputTerminal: OutputTerminal,
    OutputParameterTerminal: OutputParameterTerminal,
    InputCollectionTerminal: InputCollectionTerminal,
    OutputCollectionTerminal: OutputCollectionTerminal,

    // export required for unit tests
    CollectionTypeDescription: CollectionTypeDescription,
    NULL_COLLECTION_TYPE_DESCRIPTION: NULL_COLLECTION_TYPE_DESCRIPTION,
    ANY_COLLECTION_TYPE_DESCRIPTION: ANY_COLLECTION_TYPE_DESCRIPTION,
};
