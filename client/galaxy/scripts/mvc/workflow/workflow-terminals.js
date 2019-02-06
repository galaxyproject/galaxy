import $ from "jquery";
import _ from "underscore";
import Backbone from "backbone";

// TODO; tie into Galaxy state?
window.workflow_globals = window.workflow_globals || {};

function CollectionTypeDescription(collectionType) {
    this.collectionType = collectionType;
    this.isCollection = true;
    this.rank = collectionType.split(":").length;
}

var NULL_COLLECTION_TYPE_DESCRIPTION = {
    isCollection: false,
    canMatch: function() {
        return false;
    },
    canMapOver: function() {
        return false;
    },
    toString: function() {
        return "NullCollectionType[]";
    },
    append: function(otherCollectionType) {
        return otherCollectionType;
    },
    equal: function(other) {
        return other === this;
    }
};

var ANY_COLLECTION_TYPE_DESCRIPTION = {
    isCollection: true,
    canMatch: function(other) {
        return NULL_COLLECTION_TYPE_DESCRIPTION !== other;
    },
    canMapOver: function() {
        return false;
    },
    toString: function() {
        return "AnyCollectionType[]";
    },
    append: function() {
        return ANY_COLLECTION_TYPE_DESCRIPTION;
    },
    equal: function(other) {
        return other === this;
    }
};

$.extend(CollectionTypeDescription.prototype, {
    append: function(otherCollectionTypeDescription) {
        if (otherCollectionTypeDescription === NULL_COLLECTION_TYPE_DESCRIPTION) {
            return this;
        }
        if (otherCollectionTypeDescription === ANY_COLLECTION_TYPE_DESCRIPTION) {
            return otherCollectionTypeDescription;
        }
        return new CollectionTypeDescription(`${this.collectionType}:${otherCollectionTypeDescription.collectionType}`);
    },
    canMatch: function(otherCollectionTypeDescription) {
        if (otherCollectionTypeDescription === NULL_COLLECTION_TYPE_DESCRIPTION) {
            return false;
        }
        if (otherCollectionTypeDescription === ANY_COLLECTION_TYPE_DESCRIPTION) {
            return true;
        }
        return otherCollectionTypeDescription.collectionType == this.collectionType;
    },
    canMapOver: function(otherCollectionTypeDescription) {
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
    },
    effectiveMapOver: function(otherCollectionTypeDescription) {
        var otherCollectionType = otherCollectionTypeDescription.collectionType;
        var effectiveCollectionType = this.collectionType.substring(
            0,
            this.collectionType.length - otherCollectionType.length - 1
        );
        return new CollectionTypeDescription(effectiveCollectionType);
    },
    equal: function(otherCollectionTypeDescription) {
        return otherCollectionTypeDescription.collectionType == this.collectionType;
    },
    toString: function() {
        return `CollectionType[${this.collectionType}]`;
    },
    _endsWith: function(str, suffix) {
        return str.indexOf(suffix, str.length - suffix.length) !== -1;
    }
});

var TerminalMapping = Backbone.Model.extend({
    initialize: function(attr) {
        this.mapOver = attr.mapOver || NULL_COLLECTION_TYPE_DESCRIPTION;
        this.terminal = attr.terminal;
        this.terminal.terminalMapping = this;
    },
    disableMapOver: function() {
        this.setMapOver(NULL_COLLECTION_TYPE_DESCRIPTION);
    },
    setMapOver: function(collectionTypeDescription) {
        // TODO: Can I use "attributes" or something to auto trigger "change"
        // event?
        this.mapOver = collectionTypeDescription;
        this.trigger("change");
    }
});

var Terminal = Backbone.Model.extend({
    initialize: function(attr) {
        this.element = attr.element;
        this.connectors = [];
    },
    connect: function(connector) {
        this.connectors.push(connector);
        if (this.node) {
            this.node.markChanged();
        }
    },
    disconnect: function(connector) {
        this.connectors.splice($.inArray(connector, this.connectors), 1);
        if (this.node) {
            this.node.markChanged();
            this.resetMappingIfNeeded();
            if (!connector.dragging) {
                connector.handle2.resetCollectionTypeSource();
            }
        }
    },
    redraw: function() {
        $.each(this.connectors, (_, c) => {
            c.redraw();
        });
    },
    destroy: function() {
        $.each(this.connectors.slice(), (_, c) => {
            c.destroy();
        });
    },
    destroyInvalidConnections: function() {
        _.each(this.connectors, connector => {
            if (connector) {
                connector.destroyIfInvalid();
            }
        });
    },
    setMapOver: function(val) {
        if (this.multiple) {
            return; // Cannot set this to be multirun...
        }

        if (!this.mapOver().equal(val)) {
            this.terminalMapping.setMapOver(val);
            _.each(this.node.output_terminals, outputTerminal => {
                outputTerminal.setMapOver(val);
            });
        }
    },
    mapOver: function() {
        if (!this.terminalMapping) {
            return NULL_COLLECTION_TYPE_DESCRIPTION;
        } else {
            return this.terminalMapping.mapOver;
        }
    },
    isMappedOver: function() {
        return this.terminalMapping && this.terminalMapping.mapOver.isCollection;
    },
    resetMapping: function() {
        this.terminalMapping.disableMapOver();
    },

    resetCollectionTypeSource: function() {
        let node = this.node;
        _.each(node.output_terminals, function(output_terminal) {
            let type_source = output_terminal.attributes.collection_type_source;
            if (type_source && output_terminal.attributes.collection_type) {
                output_terminal.attributes.collection_type = null;
                output_terminal.update(output_terminal.attributes);
            }
        });
    },

    resetMappingIfNeeded: function() {} // Subclasses should override this...
});

var OutputTerminal = Terminal.extend({
    initialize: function(attr) {
        Terminal.prototype.initialize.call(this, attr);
        this.datatypes = attr.datatypes;
    },

    resetMappingIfNeeded: function() {
        // If inputs were only mapped over to preserve
        // an output just disconnected reset these...
        if (!this.node.hasConnectedOutputTerminals() && !this.node.hasConnectedMappedInputTerminals()) {
            _.each(this.node.mappedInputTerminals(), mappedInput => {
                mappedInput.resetMappingIfNeeded();
            });
        }

        var noMappedInputs = !this.node.hasMappedOverInputTerminals();
        if (noMappedInputs) {
            this.resetMapping();
        }
    },

    resetMapping: function() {
        this.terminalMapping.disableMapOver();
        _.each(this.connectors, connector => {
            var connectedInput = connector.handle2;
            if (connectedInput) {
                // Not exactly right because this is still connected.
                // Either rewrite resetMappingIfNeeded or disconnect
                // and reconnect if valid.
                connectedInput.resetMappingIfNeeded();
                connector.destroyIfInvalid();
            }
        });
    }
});

var BaseInputTerminal = Terminal.extend({
    initialize: function(attr) {
        Terminal.prototype.initialize.call(this, attr);
        this.update(attr.input); // subclasses should implement this...
    },
    canAccept: function(other) {
        if (this._inputFilled()) {
            return false;
        } else {
            return this.attachable(other);
        }
    },
    resetMappingIfNeeded: function() {
        var mapOver = this.mapOver();
        if (!mapOver.isCollection) {
            return;
        }
        // No output terminals are counting on this being mapped
        // over if connected inputs are still mapped over or if none
        // of the outputs are connected...
        var reset = this.node.hasConnectedMappedInputTerminals() || !this.node.hasConnectedOutputTerminals();
        if (reset) {
            this.resetMapping();
        }
    },
    resetMapping: function() {
        this.terminalMapping.disableMapOver();
        if (!this.node.hasMappedOverInputTerminals()) {
            _.each(this.node.output_terminals, terminal => {
                // This shouldn't be called if there are mapped over
                // outputs.
                terminal.resetMapping();
            });
        }
    },
    connected: function() {
        return this.connectors.length !== 0;
    },
    _inputFilled: function() {
        var inputFilled;
        if (!this.connected()) {
            inputFilled = false;
        } else {
            if (this.multiple) {
                if (this._collectionAttached()) {
                    // Can only attach one collection to multiple input
                    // data parameter.
                    inputFilled = true;
                } else {
                    inputFilled = false;
                }
            } else {
                inputFilled = true;
            }
        }
        return inputFilled;
    },
    _collectionAttached: function() {
        if (!this.connected()) {
            return false;
        } else {
            var firstOutput = this.connectors[0].handle1;
            if (!firstOutput) {
                return false;
            } else {
                if (
                    firstOutput.isCollection ||
                    firstOutput.isMappedOver() ||
                    firstOutput.datatypes.indexOf("input_collection") > 0
                ) {
                    return true;
                } else {
                    return false;
                }
            }
        }
    },
    _mappingConstraints: function() {
        // If this is a connected terminal, return list of collection types
        // other terminals connected to node are constraining mapping to.
        if (!this.node) {
            return []; // No node - completely unconstrained
        }
        var mapOver = this.mapOver();
        if (mapOver.isCollection) {
            return [mapOver];
        }

        var constraints = [];
        if (!this.node.hasConnectedOutputTerminals()) {
            _.each(this.node.connectedMappedInputTerminals(), inputTerminal => {
                constraints.push(inputTerminal.mapOver());
            });
        } else {
            // All outputs should have same mapOver status - least specific.
            constraints.push(_.first(_.values(this.node.output_terminals)).mapOver());
        }
        return constraints;
    },
    _producesAcceptableDatatype: function(other) {
        // other is a non-collection output...
        for (var t in this.datatypes) {
            var thisDatatype = this.datatypes[t];
            if (thisDatatype == "input") {
                return true;
            }
            var cat_outputs = [];
            cat_outputs = cat_outputs.concat(other.datatypes);
            if (other.node.post_job_actions) {
                for (var pja_i in other.node.post_job_actions) {
                    var pja = other.node.post_job_actions[pja_i];
                    if (
                        pja.action_type == "ChangeDatatypeAction" &&
                        (pja.output_name === "" || pja.output_name == other.name) &&
                        pja.action_arguments
                    ) {
                        cat_outputs.push(pja.action_arguments.newtype);
                    }
                }
            }
            // FIXME: No idea what to do about case when datatype is 'input'
            for (var other_datatype_i in cat_outputs) {
                var other_datatype = cat_outputs[other_datatype_i];
                if (
                    other_datatype == "input" ||
                    other_datatype == "_sniff_" ||
                    other_datatype == "input_collection" ||
                    window.workflow_globals.app.isSubType(cat_outputs[other_datatype_i], thisDatatype)
                ) {
                    return true;
                }
            }
        }
        return false;
    },
    _otherCollectionType: function(other) {
        var otherCollectionType = NULL_COLLECTION_TYPE_DESCRIPTION;
        if (other.isCollection) {
            otherCollectionType = other.collectionType;
        }
        var otherMapOver = other.mapOver();
        if (otherMapOver.isCollection) {
            otherCollectionType = otherMapOver.append(otherCollectionType);
        }
        return otherCollectionType;
    }
});

var InputTerminal = BaseInputTerminal.extend({
    update: function(input) {
        this.datatypes = input.extensions;
        this.multiple = input.multiple;
        this.collection = false;
    },
    connect: function(connector) {
        BaseInputTerminal.prototype.connect.call(this, connector);
        var other_output = connector.handle1;
        if (!other_output) {
            return;
        }
        var otherCollectionType = this._otherCollectionType(other_output);
        if (otherCollectionType.isCollection) {
            this.setMapOver(otherCollectionType);
        }
    },
    attachable: function(other) {
        var otherCollectionType = this._otherCollectionType(other);
        var thisMapOver = this.mapOver();
        if (otherCollectionType.isCollection) {
            if (this.multiple) {
                if (this.connected() && !this._collectionAttached()) {
                    // if single inputs attached, cannot also attach a
                    // collection (yet...)
                    return false;
                }
                if (otherCollectionType.rank == 1) {
                    return this._producesAcceptableDatatype(other);
                } else {
                    // TODO: Allow subcollection mapping over this as if it were
                    // a list collection input.
                    return false;
                }
            }
            if (thisMapOver.isCollection && thisMapOver.canMatch(otherCollectionType)) {
                return this._producesAcceptableDatatype(other);
            } else {
                //  Need to check if this would break constraints...
                var mappingConstraints = this._mappingConstraints();
                if (mappingConstraints.every(_.bind(otherCollectionType.canMatch, otherCollectionType))) {
                    return this._producesAcceptableDatatype(other);
                } else {
                    return false;
                }
            }
        } else if (thisMapOver.isCollection) {
            // Attempting to match a non-collection output to an
            // explicitly collection input.
            return false;
        }
        return this._producesAcceptableDatatype(other);
    }
});

var InputParameterTerminal = BaseInputTerminal.extend({
    update: function(input) {
        this.type = input.type;
    },
    connect: function(connector) {
        BaseInputTerminal.prototype.connect.call(this, connector);
    },
    attachable: function(other) {
        return this.type == other.attributes.type;
    }
});

var InputCollectionTerminal = BaseInputTerminal.extend({
    update: function(input) {
        this.multiple = false;
        this.collection = true;
        this.collection_type = input.collection_type;
        this.datatypes = input.extensions;
        var collectionTypes = [];
        if (input.collection_types) {
            _.each(input.collection_types, collectionType => {
                collectionTypes.push(new CollectionTypeDescription(collectionType));
            });
        } else {
            collectionTypes.push(ANY_COLLECTION_TYPE_DESCRIPTION);
        }
        this.collectionTypes = collectionTypes;
    },
    connect: function(connector) {
        BaseInputTerminal.prototype.connect.call(this, connector);
        var other = connector.handle1;
        if (!other) {
            return;
        } else {
            let node = this.node;
            _.each(node.output_terminals, function(output_terminal) {
                if (output_terminal.attributes.collection_type_source && !connector.dragging) {
                    if (other.isMappedOver()) {
                        if (other.isCollection) {
                            output_terminal.attributes.collection_type = other.terminalMapping.mapOver.append(
                                other.collectionType
                            ).collectionType;
                        } else {
                            output_terminal.attributes.collection_type = other.terminalMapping.mapOver.collectionType;
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
    },
    _effectiveMapOver: function(other) {
        var collectionTypes = this.collectionTypes;
        var otherCollectionType = this._otherCollectionType(other);
        var canMatch = _.some(collectionTypes, collectionType => collectionType.canMatch(otherCollectionType));

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
    },
    _effectiveCollectionTypes: function() {
        var thisMapOver = this.mapOver();
        return _.map(this.collectionTypes, t => thisMapOver.append(t));
    },
    attachable: function(other) {
        var otherCollectionType = this._otherCollectionType(other);
        if (otherCollectionType.isCollection) {
            var effectiveCollectionTypes = this._effectiveCollectionTypes();
            var thisMapOver = this.mapOver();
            var canMatch = _.some(effectiveCollectionTypes, effectiveCollectionType =>
                effectiveCollectionType.canMatch(otherCollectionType)
            );
            if (canMatch) {
                // Only way a direct match...
                return this._producesAcceptableDatatype(other);
                // Otherwise we need to mapOver
            } else if (thisMapOver.isCollection) {
                // In this case, mapOver already set and we didn't match skipping...
                return false;
            } else if (_.some(this.collectionTypes, collectionType => otherCollectionType.canMapOver(collectionType))) {
                var effectiveMapOver = this._effectiveMapOver(other);
                if (!effectiveMapOver.isCollection) {
                    return false;
                }
                //  Need to check if this would break constraints...
                var mappingConstraints = this._mappingConstraints();
                if (mappingConstraints.every(effectiveMapOver.canMatch)) {
                    return this._producesAcceptableDatatype(other);
                }
            }
        }
        return false;
    }
});

var OutputCollectionTerminal = Terminal.extend({
    initialize: function(attr) {
        Terminal.prototype.initialize.call(this, attr);
        this.datatypes = attr.datatypes;
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
    },
    update: function(output) {
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

        let oldCollectionType = this.collectionType;
        this.collectionType = newCollectionType;
        // we need to iterate over a copy, as we slice this.connectors in the process of destroying connections
        var connectors = this.connectors.slice(0);
        if (newCollectionType.collectionType != oldCollectionType.collectionType) {
            _.each(connectors, connector => {
                connector.destroyIfInvalid(true);
            });
        }
    }
});

var OutputParameterTerminal = Terminal.extend({});

export default {
    InputTerminal: InputTerminal,
    InputParameterTerminal: InputParameterTerminal,
    OutputTerminal: OutputTerminal,
    OutputParameterTerminal: OutputParameterTerminal,
    InputCollectionTerminal: InputCollectionTerminal,
    OutputCollectionTerminal: OutputCollectionTerminal,
    TerminalMapping: TerminalMapping,

    // test export
    CollectionTypeDescription: CollectionTypeDescription,
    NULL_COLLECTION_TYPE_DESCRIPTION: NULL_COLLECTION_TYPE_DESCRIPTION,
    ANY_COLLECTION_TYPE_DESCRIPTION: ANY_COLLECTION_TYPE_DESCRIPTION
};
