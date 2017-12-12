define("mvc/dataset/dataset-choice", ["exports", "mvc/dataset/dataset-model", "mvc/dataset/dataset-list", "mvc/ui/ui-modal", "mvc/base-mvc", "utils/localization"], function(exports, _datasetModel, _datasetList, _uiModal, _baseMvc, _localization) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });

    var _datasetModel2 = _interopRequireDefault(_datasetModel);

    var _datasetList2 = _interopRequireDefault(_datasetList);

    var _uiModal2 = _interopRequireDefault(_uiModal);

    var _baseMvc2 = _interopRequireDefault(_baseMvc);

    var _localization2 = _interopRequireDefault(_localization);

    function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : {
            default: obj
        };
    }

    var logNamespace = "dataset";
    /* ============================================================================
    TODO:
        does this really work with mixed contents?
        Single dataset choice: allow none?
        tooltips rendered *behind* modal
        collection selector
        better handling when no results returned from filterDatasetJSON
        pass optional subtitle from choice display to modal
        onfirstclick
        drop target
        return modal with promise?
    
        auto showing the modal may not be best
    
    ============================================================================ */
    /** Filters an array of dataset plain JSON objs.
     */
    function _filterDatasetJSON(datasetJSON, where, datasetsOnly) {
        //TODO: replace with _.matches (underscore 1.6.0)
        function matches(obj, toMatch) {
            for (var key in toMatch) {
                if (toMatch.hasOwnProperty(key)) {
                    if (obj[key] !== toMatch[key]) {
                        return false;
                    }
                }
            }
            return true;
        }

        return datasetJSON.filter(function(json) {
            console.debug(json);
            return !json.deleted && json.visible && (!datasetsOnly || json.collection_type === undefined) && matches(json, where);
        });
    }

    // ============================================================================
    /** Given an array of plain JSON objs rep. datasets, show a modal allowing a choice
     *      of one or more of those datasets.
     *
     *  Pass:
     *      an array of plain JSON objects representing allowed dataset choices
     *      a map of options (see below)
     *
     *  Options:
     *      datasetsOnly:   T: display only datasets, F: datasets + dataset collections
     *      where:          a map of attributes available choices *must have* (defaults to { state: 'ok' })
     *      multiselect:    T: user can select more than one, F: only one
     *      selected:       array of dataset ids to make them selected by default
     *
     *  @example:
     *      var datasetJSON = // from ajax or bootstrap
     *      // returns a jQuery promise (that 'fail's only if no datasets are found matching 'where' below)
     *      var choice = new DatasetChoiceModal( datasetJSON, {
     *          datasetsOnly    : false,
     *          where           : { state: 'ok', file_ext: 'bed', ... },
     *          multiselect     : true,
     *          selected        : [ 'df7a1f0c02a5b08e', 'abcdef0123456789' ]
     *
     *      }).done( function( json ){
     *          if( json ){
     *              console.debug( json );
     *              // returned choice will always be an array (single or multi)
     *              // [{ <selected dataset JSON 1>, <selected dataset JSON 2>, ... }]
     *              // ... do stuff
     *          } else {
     *              // json will === null if the user cancelled selection
     *              console.debug( 'cancelled' );
     *          }
     *      });
     */
    var DatasetChoiceModal = function DatasetChoiceModal(datasetJSON, options) {
        // option defaults
        options = _.defaults(options || {}, {
            // show datasets or datasets and collections
            datasetsOnly: true,
            // map of attributes to filter datasetJSON by
            where: {
                state: "ok"
            },
            // select more than one dataset?
            multiselect: false,
            // any dataset ids that will display as already selected
            selected: []
        });
        // default title should depend on multiselect
        options.title = options.title || (options.multiselect ? (0, _localization2.default)("Choose datasets:") : (0, _localization2.default)("Choose a dataset:"));

        var modal;
        var list;
        var buttons;
        var promise = jQuery.Deferred();
        var filterFn = options.filter || _filterDatasetJSON;

        // filter the given datasets and if none left return a rejected promise for use with fail()
        datasetJSON = filterFn(datasetJSON, options.where, options.datasetsOnly);
        if (!datasetJSON.length) {
            return promise.reject("No matches found");
        }

        // resolve the returned promise with the json of the selected datasets
        function resolveWithSelected() {
            promise.resolve(list.getSelectedModels().map(function(model) {
                return model.toJSON();
            }));
        }
        // if multiselect - add a button for the user to complete the changes
        if (options.multiselect) {
            buttons = {};
            buttons[(0, _localization2.default)("Ok")] = resolveWithSelected;
        }

        // create a full-height modal that's cancellable, remove unneeded elements and styles
        modal = new _uiModal2.default.View({
            height: "auto",
            buttons: buttons,
            closing_events: true,
            closing_callback: function closing_callback() {
                promise.resolve(null);
            },
            body: ['<div class="list-panel"></div>'].join("")
        });
        modal.$(".modal-header").remove();
        modal.$(".modal-footer").css("margin-top", "0px");

        // attach a dataset list (of the filtered datasets) to that modal that's selectable
        list = new _datasetList2.default.DatasetList({
            title: options.title,
            subtitle: options.subtitle || (0, _localization2.default)([
                //TODO: as option
                "Click the checkboxes on the right to select datasets. ", "Click the datasets names to see their details. "
            ].join("")),
            el: modal.$body.find(".list-panel"),
            selecting: true,
            selected: options.selected,
            collection: new _datasetModel2.default.DatasetAssociationCollection(datasetJSON)
        });

        // when the list is rendered, show the modal (also add a specifying class for css)
        list.once("rendered:initial", function() {
            modal.show();
            modal.$el.addClass("dataset-choice-modal");
        });
        if (!options.multiselect) {
            // if single select, remove the all/none list actions from the panel
            list.on("rendered", function() {
                list.$(".list-actions").hide();
            });
            // if single select, immediately resolve on a single selection
            list.on("view:selected", function(view) {
                promise.resolve([view.model.toJSON()]);
            });
        }
        list.render(0);

        // return the promise, and on any resolution close the modal
        return promise.always(function() {
            modal.hide();
        });
    };

    // ============================================================================
    /** Activator for single dataset selection modal and display of the selected dataset.
     *      The activator/display will show as a single div and, when a dataset is selected,
     *      show the name and details of the selected dataset.
     *
     *      When clicked the div will generate a DatasetChoiceModal of the available choices.
     *
     *  Options:
     *      datasetJSON:    array of plain json objects representing allowed choices
     *      datasetsOnly:   T: only show datasets in the allowed choices, F: datasets + collections
     *      where:          map of attributes to filter datasetJSON by (e.g. { file_ext: 'bed' })
     *      label:          the label/prompt displayed
     *      selected:       array of dataset ids that will show as already selected in the control
     *
     *  @example:
     *      var choice1 = new DATASET_CHOICE.DatasetChoice({
     *          datasetJSON : datasetJSON,
     *          label       : 'Input dataset',
     *          selected    : [ 'df7a1f0c02a5b08e' ]
     *      });
     *      $( 'body' ).append( choice1.render().$el )
     *
     *  Listen to the DatasetChoice to react to changes in the user's choice/selection:
     *  @example:
     *      choice1.on( 'selected', function( chooser, selectionJSONArray ){
     *          // ... do stuff with new selections
     *      });
     */
    var DatasetChoice = Backbone.View.extend(_baseMvc2.default.LoggableMixin).extend({
        _logNamespace: logNamespace,

        className: "dataset-choice",

        /** set up defaults, options, and listeners */
        initialize: function initialize(attributes) {
            this.debug(this + "(DatasetChoice).initialize:", attributes);

            this.label = attributes.label !== undefined ? (0, _localization2.default)(attributes.label) : "";
            this.where = attributes.where;
            this.datasetsOnly = attributes.datasetsOnly !== undefined ? attributes.datasetsOnly : true;

            this.datasetJSON = attributes.datasetJSON || [];
            this.selected = attributes.selected || [];

            this._setUpListeners();
        },

        /** add any (bbone) listeners */
        _setUpListeners: function _setUpListeners() {
            //this.on( 'all', function(){
            //    this.log( this + '', arguments );
            //});
        },

        /** render the view */
        render: function render() {
            var json = this.toJSON();
            this.$el.html(this._template(json));
            this.$(".selected").replaceWith(this._renderSelected(json));
            return this;
        },

        /** return plain html for the overall control */
        _template: function _template(json) {
            return _.template(["<label>", '<span class="prompt"><%- label %></span>', '<div class="selected"></div>', "</label>"].join(""))(json);
        },

        /** return jQ DOM for the selected dataset (only one) */
        _renderSelected: function _renderSelected(json) {
            if (json.selected.length) {
                //TODO: break out?
                return $(_.template(['<div class="selected">', '<span class="title"><%- selected.hid %>: <%- selected.name %></span>', '<span class="subtitle">', "<i><%- selected.misc_blurb %></i>", "<i>", (0, _localization2.default)("format") + ": ", "<%- selected.file_ext %></i>", "<i><%- selected.misc_info %></i>", "</span>", "</div>"].join(""), {
                    variable: "selected"
                })(json.selected[0]));
            }
            return $(['<span class="none-selected-msg">(', (0, _localization2.default)("click to select a dataset"), ")</span>"].join(""));
        },

        //TODO:?? why not just pass in view?
        /** return a plain JSON object with both the view and dataset attributes */
        toJSON: function toJSON() {
            var chooser = this;
            return {
                label: chooser.label,
                datasets: chooser.datasetJSON,
                selected: _.compact(_.map(chooser.selected, function(id) {
                    return _.findWhere(chooser.datasetJSON, {
                        id: id
                    });
                }))
            };
        },

        /** event map: when to open the modal */
        events: {
            // the whole thing functions as a button
            click: "chooseWithModal"
        },

        //TODO:?? modal to prop of this?
        //TODO:?? should be able to handle 'none selectable' on initialize
        /** open the modal and handle the promise representing the user's choice
         *  @fires 'selected' when the user selects dataset(s) - passed full json of the selected datasets
         *  @fires 'cancelled' when the user clicks away/closes the modal (no selection made) - passed this
         *  @fires 'error' if the modal has no selectable datasets based on this.where - passed this and other args
         */
        chooseWithModal: function chooseWithModal() {
            var chooser = this;

            return this._createModal().done(function(json) {
                if (json) {
                    chooser.selected = _.pluck(json, "id");
                    chooser.trigger("selected", chooser, json);
                    chooser.render();
                } else {
                    chooser.trigger("cancelled", chooser);
                }
            }).fail(function() {
                chooser.trigger("error", chooser, arguments);
            });
        },

        /** create and return the modal to use for choosing */
        _createModal: function _createModal() {
            return new DatasetChoiceModal(this.datasetJSON, this._getModalOptions());
        },

        /** return a plain JSON containing the options to pass to the modal */
        _getModalOptions: function _getModalOptions() {
            return {
                title: this.label,
                multiselect: false,
                selected: this.selected,
                where: this.where,
                datasetsOnly: this.datasetsOnly
            };
        },

        // ------------------------------------------------------------------------ misc
        /** string rep */
        toString: function toString() {
            return "DatasetChoice(" + this.selected + ")";
        }
    });

    // ============================================================================
    /** Activator for multiple dataset selection modal and display of the selected datasets.
     *      The activator/display will show as a table of all choices.
     *
     *  See DatasetChoice (above) for example usage.
     *
     *  Additional options:
     *      showHeaders:    T: show headers for selected dataset attributes in the display table
     *      cells:          map of attribute keys -> Human readable/localized column headers
     *          (e.g. { file_ext: _l( 'Format' ) }) - defaults are listed below
     */
    var MultiDatasetChoice = DatasetChoice.extend({
        className: DatasetChoice.prototype.className + " multi",

        /** default (dataset attribute key -> table header text) map of what cells to display in the table */
        cells: {
            hid: (0, _localization2.default)("History #"),
            name: (0, _localization2.default)("Name"),
            misc_blurb: (0, _localization2.default)("Summary"),
            file_ext: (0, _localization2.default)("Format"),
            genome_build: (0, _localization2.default)("Genome"),
            tags: (0, _localization2.default)("Tags"),
            annotation: (0, _localization2.default)("Annotation")
        },

        /** in this override, add the showHeaders and cells options */
        initialize: function initialize(attributes) {
            this.showHeaders = attributes.showHeaders !== undefined ? attributes.showHeaders : true;
            this.cells = attributes.cells || this.cells;
            DatasetChoice.prototype.initialize.call(this, attributes);
        },

        /** in this override, display the selected datasets as a table with optional headers */
        _renderSelected: function _renderSelected(json) {
            if (json.selected.length) {
                return $(_.template(['<table class="selected">', "<% if( json.showHeaders ){ %>", "<thead><tr>", "<% _.map( json.cells, function( val, key ){ %>", "<th><%- val %></th>", "<% }); %>", "</tr></thead>", "<% } %>", "<tbody>", "<% _.map( json.selected, function( selected ){ %>", "<tr>", "<% _.map( json.cells, function( val, key ){ %>", '<td class="cell-<%- key %>"><%- selected[ key ] %></td>', "<% }) %>", "</tr>", "<% }); %>", "</tbody>", "</table>"].join(""), {
                    variable: "json"
                })(json));
            }
            return $(['<span class="none-selected-msg">(', (0, _localization2.default)("click to select a dataset"), ")</span>"].join(""));
        },

        /** in this override, send the showHeaders and cells options as well */
        toJSON: function toJSON() {
            return _.extend(DatasetChoice.prototype.toJSON.call(this), {
                showHeaders: this.showHeaders,
                cells: this.cells
            });
        },

        /** in this override, set multiselect to true */
        _getModalOptions: function _getModalOptions() {
            return _.extend(DatasetChoice.prototype._getModalOptions.call(this), {
                multiselect: true
            });
        },

        // ------------------------------------------------------------------------ misc
        /** string rep */
        toString: function toString() {
            return "DatasetChoice(" + this.selected + ")";
        }
    });

    // ============================================================================
    exports.default = {
        DatasetChoiceModal: DatasetChoiceModal,
        DatasetChoice: DatasetChoice,
        MultiDatasetChoice: MultiDatasetChoice
    };
});
//# sourceMappingURL=../../../maps/mvc/dataset/dataset-choice.js.map
