define("mvc/collection/collection-model", ["exports", "mvc/dataset/dataset-model", "mvc/base-mvc", "utils/localization"], function(exports, _datasetModel, _baseMvc, _localization) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });

    var _datasetModel2 = _interopRequireDefault(_datasetModel);

    var _baseMvc2 = _interopRequireDefault(_baseMvc);

    var _localization2 = _interopRequireDefault(_localization);

    function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : {
            default: obj
        };
    }

    //==============================================================================
    /*
    Notes:
    
    Terminology:
        DatasetCollection/DC : a container of datasets or nested DatasetCollections
        Element/DatasetCollectionElement/DCE : an item contained in a DatasetCollection
        HistoryDatasetCollectionAssociation/HDCA: a DatasetCollection contained in a history
    
    
    This all seems too complex unfortunately:
    
    - Terminology collision between DatasetCollections (DCs) and Backbone Collections.
    - In the DatasetCollections API JSON, DC Elements use a 'Has A' stucture to *contain*
        either a dataset or a nested DC. This would make the hierarchy much taller. I've
        decided to merge the contained JSON with the DC element json - making the 'has a'
        relation into an 'is a' relation. This seems simpler to me and allowed a lot of
        DRY in both models and views, but may make tracking or tracing within these models
        more difficult (since DatasetCollectionElements are now *also* DatasetAssociations
        or DatasetCollections (nested)). This also violates the rule of thumb about
        favoring aggregation over inheritance.
    - Currently, there are three DatasetCollection subclasses: List, Pair, and ListPaired.
        These each should a) be usable on their own, b) be usable in the context of
        nesting within a collection model (at least in the case of ListPaired), and
        c) be usable within the context of other container models (like History or
        LibraryFolder, etc.). I've tried to separate/extract classes in order to
        handle those three situations, but it's proven difficult to do in a simple,
        readable manner.
    - Ideally, histories and libraries would inherit from the same server models as
        dataset collections do since they are (in essence) dataset collections themselves -
        making the whole nested structure simpler. This would be a large, error-prone
        refactoring and migration.
    
    Many of the classes and heirarchy are meant as extension points so, while the
    relations and flow may be difficult to understand initially, they'll allow us to
    handle the growth or flux dataset collection in the future (w/o actually implementing
    any YAGNI).
    
    */
    //_________________________________________________________________________________________________ ELEMENTS
    /** @class mixin for Dataset collection elements.
     *      When collection elements are passed from the API, the underlying element is
     *          in a sub-object 'object' (IOW, a DCE representing an HDA will have HDA json in element.object).
     *      This mixin uses the constructor and parse methods to merge that JSON with the DCE attribtues
     *          effectively changing a DCE from a container to a subclass (has a --> is a).
     */
    var DatasetCollectionElementMixin = {
        /** default attributes used by elements in a dataset collection */
        defaults: {
            model_class: "DatasetCollectionElement",
            element_identifier: null,
            element_index: null,
            element_type: null
        },

        /** merge the attributes of the sub-object 'object' into this model */
        _mergeObject: function _mergeObject(attributes) {
            // if we don't preserve and correct ids here, the element id becomes the object id
            // and collision in backbone's _byId will occur and only
            _.extend(attributes, attributes.object, {
                element_id: attributes.id
            });
            delete attributes.object;
            return attributes;
        },

        /** override to merge this.object into this */
        constructor: function constructor(attributes, options) {
            // console.debug( '\t DatasetCollectionElement.constructor:', attributes, options );
            attributes = this._mergeObject(attributes);
            this.idAttribute = "element_id";
            Backbone.Model.apply(this, arguments);
        },

        /** when the model is fetched, merge this.object into this */
        parse: function parse(response, options) {
            var attributes = response;
            attributes = this._mergeObject(attributes);
            return attributes;
        }
    };

    /** @class Concrete class of Generic DatasetCollectionElement */
    var DatasetCollectionElement = Backbone.Model.extend(_baseMvc2.default.LoggableMixin).extend(DatasetCollectionElementMixin).extend({
        _logNamespace: "collections"
    });

    //==============================================================================
    /** @class Base/Abstract Backbone collection for Generic DCEs - 
        current may be associated with a dataset (DatasetDCECollection)
        or another collection (NestedDCDCECollection).
    */
    var DCECollection = Backbone.Collection.extend(_baseMvc2.default.LoggableMixin).extend(
        /** @lends DCECollection.prototype */
        {
            _logNamespace: "collections",

            model: DatasetCollectionElement,

            /** String representation. */
            toString: function toString() {
                return ["DatasetCollectionElementCollection(", this.length, ")"].join("");
            }
        });

    //==============================================================================
    /** @class Backbone model for a dataset collection element that is a dataset (HDA).
     */
    var DatasetDCE = _datasetModel2.default.DatasetAssociation.extend(_baseMvc2.default.mixin(DatasetCollectionElementMixin,
        /** @lends DatasetDCE.prototype */
        {
            /** url fn */
            url: function url() {
                // won't always be an hda
                if (!this.has("history_id")) {
                    console.warn("no endpoint for non-hdas within a collection yet");
                    // (a little silly since this api endpoint *also* points at hdas)
                    return Galaxy.root + "api/datasets";
                }
                return Galaxy.root + "api/histories/" + this.get("history_id") + "/contents/" + this.get("id");
            },

            defaults: _.extend({}, _datasetModel2.default.DatasetAssociation.prototype.defaults, DatasetCollectionElementMixin.defaults),

            _downloadQueryParameters: function _downloadQueryParameters() {
                var fileExt = this.get("file_ext");
                var elementIdentifier = this.get("element_identifier");
                var parentHdcaId = this.get("parent_hdca_id");
                return "?to_ext=" + fileExt + "&hdca_id=" + parentHdcaId + "&element_identifier=" + elementIdentifier;
            },

            // because all objects have constructors (as this hashmap would even if this next line wasn't present)
            //  the constructor in hcontentMixin won't be attached by BASE_MVC.mixin to this model
            //  - re-apply manually for now
            /** call the mixin constructor */
            constructor: function constructor(attributes, options) {
                this.debug("\t DatasetDCE.constructor:", attributes, options);
                //DATASET_MODEL.DatasetAssociation.prototype.constructor.call( this, attributes, options );
                DatasetCollectionElementMixin.constructor.call(this, attributes, options);
            },

            /** Does this model already contain detailed data (as opposed to just summary level data)? */
            hasDetails: function hasDetails() {
                return this.elements && this.elements.length;
            },

            /** String representation. */
            toString: function toString() {
                var objStr = this.get("element_identifier");
                return "DatasetDCE({objStr})";
            }
        }));

    //==============================================================================
    /** @class DCECollection of DatasetDCE's (a list of datasets, a pair of datasets).
     */
    var DatasetDCECollection = DCECollection.extend(
        /** @lends DatasetDCECollection.prototype */
        {
            model: DatasetDCE,

            /** String representation. */
            toString: function toString() {
                return ["DatasetDCECollection(", this.length, ")"].join("");
            }
        });

    //_________________________________________________________________________________________________ COLLECTIONS
    /** @class Backbone model for Dataset Collections.
     *      The DC API returns an array of JSON objects under the attribute elements.
     *      This model:
     *          - removes that array/attribute ('elements') from the model,
     *          - creates a bbone collection (of the class defined in the 'collectionClass' attribute),
     *          - passes that json onto the bbone collection
     *          - caches the bbone collection in this.elements
     */
    var DatasetCollection = Backbone.Model.extend(_baseMvc2.default.LoggableMixin).extend(_baseMvc2.default.SearchableModelMixin).extend(
        /** @lends DatasetCollection.prototype */
        {
            _logNamespace: "collections",

            /** default attributes for a model */
            defaults: {
                /* 'list', 'paired', or 'list:paired' */
                collection_type: null,
                //??
                deleted: false
            },

            /** Which class to use for elements */
            collectionClass: function collectionClass() {
                if (this.attributes.collection_type.indexOf(":") > 0) {
                    return NestedDCDCECollection;
                } else {
                    return DatasetDCECollection;
                }
            },

            /** set up: create elements instance var and (on changes to elements) update them  */
            initialize: function initialize(model, options) {
                this.debug(this + "(DatasetCollection).initialize:", model, options, this);
                this.elements = this._createElementsModel();
                this.on("change:elements", function() {
                    this.log("change:elements");
                    //TODO: prob. better to update the collection instead of re-creating it
                    this.elements = this._createElementsModel();
                });
            },

            /** move elements model attribute to full collection */
            _createElementsModel: function _createElementsModel() {
                var collectionClass = this.collectionClass();
                this.debug(this + "._createElementsModel", collectionClass, this.get("elements"), this.elements);
                //TODO: same patterns as DatasetCollectionElement _createObjectModel - refactor to BASE_MVC.hasSubModel?
                var elements = this.get("elements") || [];
                this.unset("elements", {
                    silent: true
                });
                var self = this;
                _.each(elements, function(element, index) {
                    _.extend(element, {
                        parent_hdca_id: self.get("id")
                    });
                });
                this.elements = new collectionClass(elements);
                //this.debug( 'collectionClass:', this.collectionClass + '', this.elements );
                return this.elements;
            },

            // ........................................................................ common queries
            /** pass the elements back within the model json when this is serialized */
            toJSON: function toJSON() {
                var json = Backbone.Model.prototype.toJSON.call(this);
                if (this.elements) {
                    json.elements = this.elements.toJSON();
                }
                return json;
            },

            /** Is this collection in a 'ready' state no processing (for the collection) is left
             *  to do on the server.
             */
            inReadyState: function inReadyState() {
                var populated = this.get("populated");
                return this.isDeletedOrPurged() || populated;
            },

            //TODO:?? the following are the same interface as DatasetAssociation - can we combine?
            /** Does the DC contain any elements yet? Is a fetch() required? */
            hasDetails: function hasDetails() {
                return this.elements.length !== 0;
            },

            /** Given the filters, what models in this.elements would be returned? */
            getVisibleContents: function getVisibleContents(filters) {
                // filters unused for now
                return this.elements;
            },

            // ........................................................................ ajax
            /** override to use actual Dates objects for create/update times */
            parse: function parse(response, options) {
                var parsed = Backbone.Model.prototype.parse.call(this, response, options);
                if (parsed.create_time) {
                    parsed.create_time = new Date(parsed.create_time);
                }
                if (parsed.update_time) {
                    parsed.update_time = new Date(parsed.update_time);
                }
                return parsed;
            },

            /** save this dataset, _Mark_ing it as deleted (just a flag) */
            delete: function _delete(options) {
                if (this.get("deleted")) {
                    return jQuery.when();
                }
                return this.save({
                    deleted: true
                }, options);
            },
            /** save this dataset, _Mark_ing it as undeleted */
            undelete: function undelete(options) {
                if (!this.get("deleted") || this.get("purged")) {
                    return jQuery.when();
                }
                return this.save({
                    deleted: false
                }, options);
            },

            /** Is this collection deleted or purged? */
            isDeletedOrPurged: function isDeletedOrPurged() {
                return this.get("deleted") || this.get("purged");
            },

            // ........................................................................ searchable
            /** searchable attributes for collections */
            searchAttributes: ["name", "tags"],

            // ........................................................................ misc
            /** String representation */
            toString: function toString() {
                var idAndName = [this.get("id"), this.get("name") || this.get("element_identifier")];
                return "DatasetCollection(" + idAndName.join(",") + ")";
            }
        });

    //_________________________________________________________________________________________________ NESTED COLLECTIONS
    // this is where things get weird, man. Weird.
    //TODO: it might be possible to compact all the following...I think.
    //==============================================================================
    /** @class Backbone model for a Generic DatasetCollectionElement that is also a DatasetCollection
     *      (a nested collection).
     */
    var NestedDCDCE = DatasetCollection.extend(_baseMvc2.default.mixin(DatasetCollectionElementMixin,
        /** @lends NestedDCDCE.prototype */
        {
            // because all objects have constructors (as this hashmap would even if this next line wasn't present)
            //  the constructor in hcontentMixin won't be attached by BASE_MVC.mixin to this model
            //  - re-apply manually it now
            /** call the mixin constructor */
            constructor: function constructor(attributes, options) {
                this.debug("\t NestedDCDCE.constructor:", attributes, options);
                DatasetCollectionElementMixin.constructor.call(this, attributes, options);
            },

            /** String representation. */
            toString: function toString() {
                var objStr = this.object ? "" + this.object : this.get("element_identifier");
                return ["NestedDCDCE(", objStr, ")"].join("");
            }
        }));

    //==============================================================================
    /** @class Backbone collection containing Generic NestedDCDCE's (nested dataset collections).
     */
    var NestedDCDCECollection = DCECollection.extend(
        /** @lends NestedDCDCECollection.prototype */
        {
            /** This is a collection of nested collections */
            model: NestedDCDCE,

            /** String representation. */
            toString: function toString() {
                return ["NestedDCDCECollection(", this.length, ")"].join("");
            }
        });

    //==============================================================================
    exports.default = {
        DatasetCollection: DatasetCollection
    };
});
//# sourceMappingURL=../../../maps/mvc/collection/collection-model.js.map
