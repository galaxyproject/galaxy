define("mvc/visualization/visualization-model", ["exports", "libs/backbone"], function(exports, _backbone) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });
    exports.VisualizationCollection = exports.Visualization = undefined;

    var Backbone = _interopRequireWildcard(_backbone);

    function _interopRequireWildcard(obj) {
        if (obj && obj.__esModule) {
            return obj;
        } else {
            var newObj = {};

            if (obj != null) {
                for (var key in obj) {
                    if (Object.prototype.hasOwnProperty.call(obj, key)) newObj[key] = obj[key];
                }
            }

            newObj.default = obj;
            return newObj;
        }
    }

    //==============================================================================
    /** @class Model for a saved Galaxy visualization.
     *
     *  @augments Backbone.Model
     *  @constructs
     */
    var Visualization = exports.Visualization = Backbone.Model.extend(
        /** @lends Visualization.prototype */
        {
            ///** logger used to record this.log messages, commonly set to console */
            //// comment this out to suppress log output
            //logger              : console,

            /** default attributes for a model */
            defaults: {
                config: {}
            },

            /** override urlRoot to handle prefix */
            urlRoot: function urlRoot() {
                var apiUrl = "api/visualizations";
                return Galaxy.root + apiUrl;
            },

            /** Set up the model, determine if accessible, bind listeners
             *  @see Backbone.Model#initialize
             */
            initialize: function initialize(data) {
                //this.log( this + '.initialize', data, this.attributes );

                // munge config sub-object here since bbone won't handle defaults with this
                if (_.isObject(data.config) && _.isObject(this.defaults.config)) {
                    _.defaults(data.config, this.defaults.config);
                }

                this._setUpListeners();
            },

            /** set up any event listeners
             */
            _setUpListeners: function _setUpListeners() {
                //this.on( 'change', function(){
                //    console.info( 'change:', arguments );
                //});
            },

            // ........................................................................ config
            /** override set to properly allow update and trigger change when setting the sub-obj 'config' */
            set: function set(key, val) {
                //TODO: validate config is object
                if (key === "config") {
                    var oldConfig = this.get("config");
                    // extend if already exists (is this correct behavior? no way to eliminate keys or reset entirely)
                    // clone in order to trigger change (diff. obj ref)
                    if (_.isObject(oldConfig)) {
                        val = _.extend(_.clone(oldConfig), val);
                    }
                }
                Backbone.Model.prototype.set.call(this, key, val);
                return this;
            },

            // ........................................................................ misc
            /** String representation */
            toString: function toString() {
                var idAndTitle = this.get("id") || "";
                if (this.get("title")) {
                    idAndTitle += ":" + this.get("title");
                }
                return "Visualization(" + idAndTitle + ")";
            }
        });

    //==============================================================================
    /** @class Backbone collection of visualization models
     *
     *  @constructs
     */
    var VisualizationCollection = exports.VisualizationCollection = Backbone.Collection.extend(
        /** @lends VisualizationCollection.prototype */
        {
            model: Visualization,

            ///** logger used to record this.log messages, commonly set to console */
            //// comment this out to suppress log output
            //logger              : console,

            url: function url() {
                return Galaxy.root + "api/visualizations";
            },

            /** Set up.
             *  @see Backbone.Collection#initialize
             */
            initialize: function initialize(models, options) {
                options = options || {};
                //this._setUpListeners();
            },

            //_setUpListeners : function(){
            //},

            // ........................................................................ common queries
            // ........................................................................ ajax
            // ........................................................................ misc
            set: function set(models, options) {
                // arrrrrrrrrrrrrrrrrg...
                // override to get a correct/smarter merge when incoming data is partial (e.g. stupid backbone)
                //  w/o this partial models from the server will fill in missing data with model defaults
                //  and overwrite existing data on the client
                // see Backbone.Collection.set and _prepareModel
                var collection = this;
                models = _.map(models, function(model) {
                    var existing = collection.get(model.id);
                    if (!existing) {
                        return model;
                    }

                    // merge the models _BEFORE_ calling the superclass version
                    var merged = existing.toJSON();
                    _.extend(merged, model);
                    return merged;
                });
                // now call superclass when the data is filled
                Backbone.Collection.prototype.set.call(this, models, options);
            },

            /** String representation. */
            toString: function toString() {
                return ["VisualizationCollection(", [this.historyId, this.length].join(), ")"].join("");
            }
        });
});
//# sourceMappingURL=../../../maps/mvc/visualization/visualization-model.js.map
