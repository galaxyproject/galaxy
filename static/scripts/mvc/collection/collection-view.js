define("mvc/collection/collection-view", ["exports", "mvc/list/list-view", "mvc/collection/collection-model", "mvc/collection/collection-li", "mvc/base-mvc", "utils/localization"], function(exports, _listView, _collectionModel, _collectionLi, _baseMvc, _localization) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });

    var _listView2 = _interopRequireDefault(_listView);

    var _collectionModel2 = _interopRequireDefault(_collectionModel);

    var _collectionLi2 = _interopRequireDefault(_collectionLi);

    var _baseMvc2 = _interopRequireDefault(_baseMvc);

    var _localization2 = _interopRequireDefault(_localization);

    function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : {
            default: obj
        };
    }

    var logNamespace = "collections";
    /* =============================================================================
    TODO:
    
    ============================================================================= */
    /** @class non-editable, read-only View/Controller for a dataset collection.
     */
    var _super = _listView2.default.ModelListPanel;
    var CollectionView = _super.extend(
        /** @lends CollectionView.prototype */
        {
            //MODEL is either a DatasetCollection (or subclass) or a DatasetCollectionElement (list of pairs)
            _logNamespace: logNamespace,

            className: _super.prototype.className + " dataset-collection-panel",

            /** sub view class used for datasets */
            DatasetDCEViewClass: _collectionLi2.default.DatasetDCEListItemView,

            /** key of attribute in model to assign to this.collection */
            modelCollectionKey: "elements",

            // ......................................................................... SET UP
            /** Set up the view, set up storage, bind listeners to HistoryContents events
             *  @param {Object} attributes optional settings for the panel
             */
            initialize: function initialize(attributes) {
                _super.prototype.initialize.call(this, attributes);
                this.linkTarget = attributes.linkTarget || "_blank";

                this.hasUser = attributes.hasUser;
                /** A stack of panels that currently cover or hide this panel */
                this.panelStack = [];
                /** The text of the link to go back to the panel containing this one */
                this.parentName = attributes.parentName;
                /** foldout or drilldown */
                this.foldoutStyle = attributes.foldoutStyle || "foldout";
                this.downloadUrl = Galaxy.root + "api/dataset_collections/" + this.model.attributes.id + "/download";
            },

            getNestedDCDCEViewClass: function getNestedDCDCEViewClass() {
                return _collectionLi2.default.NestedDCDCEListItemView.extend({
                    foldoutPanelClass: CollectionView
                });
            },

            _queueNewRender: function _queueNewRender($newRender, speed) {
                speed = speed === undefined ? this.fxSpeed : speed;
                var panel = this;
                this.handleWarning($newRender);
                panel.log("_queueNewRender:", $newRender, speed);

                // TODO: jquery@1.12 doesn't change display when the elem has display: flex
                // this causes display: block for those elems after the use of show/hide animations
                // animations are removed from this view for now until fixed
                panel._swapNewRender($newRender);
                panel.trigger("rendered", panel);
            },

            handleWarning: function handleWarning($newRender) {
                var viewLength = this.views.length;
                var elementCount = this.model.get("element_count");
                if (elementCount && elementCount !== viewLength) {
                    var warning = (0, _localization2.default)("displaying only " + viewLength + " of " + elementCount + " items");
                    var $warns = $newRender.find(".elements-warning");
                    $warns.html("<div class=\"warningmessagesmall\">" + warning + "</div>");
                }
            },

            // ------------------------------------------------------------------------ sub-views
            /** In this override, use model.getVisibleContents */
            _filterCollection: function _filterCollection() {
                //TODO: should *not* be model.getVisibleContents - visibility is not model related
                return this.model.getVisibleContents();
            },

            /** override to return proper view class based on element_type */
            _getItemViewClass: function _getItemViewClass(model) {
                //this.debug( this + '._getItemViewClass:', model );
                //TODO: subclasses use DCEViewClass - but are currently unused - decide
                switch (model.get("element_type")) {
                    case "hda":
                        return this.DatasetDCEViewClass;
                    case "dataset_collection":
                        return this.getNestedDCDCEViewClass();
                }
                throw new TypeError("Unknown element type:", model.get("element_type"));
            },

            /** override to add link target and anon */
            _getItemViewOptions: function _getItemViewOptions(model) {
                var options = _super.prototype._getItemViewOptions.call(this, model);
                return _.extend(options, {
                    linkTarget: this.linkTarget,
                    hasUser: this.hasUser,
                    //TODO: could move to only nested: list:paired
                    foldoutStyle: this.foldoutStyle
                });
            },

            // ------------------------------------------------------------------------ collection sub-views
            /** In this override, add/remove expanded/collapsed model ids to/from web storage */
            _setUpItemViewListeners: function _setUpItemViewListeners(view) {
                var panel = this;
                _super.prototype._setUpItemViewListeners.call(panel, view);

                // use pub-sub to: handle drilldown expansion and collapse
                panel.listenTo(view, {
                    "expanded:drilldown": function expandedDrilldown(v, drilldown) {
                        this._expandDrilldownPanel(drilldown);
                    },
                    "collapsed:drilldown": function collapsedDrilldown(v, drilldown) {
                        this._collapseDrilldownPanel(drilldown);
                    }
                });
                return this;
            },

            /** Handle drill down by hiding this panels list and controls and showing the sub-panel */
            _expandDrilldownPanel: function _expandDrilldownPanel(drilldown) {
                this.panelStack.push(drilldown);
                // hide this panel's controls and list, set the name for back navigation, and attach to the $el
                this.$("> .controls").add(this.$list()).hide();
                drilldown.parentName = this.model.get("name");
                this.$el.append(drilldown.render().$el);
            },

            /** Handle drilldown close by freeing the panel and re-rendering this panel */
            _collapseDrilldownPanel: function _collapseDrilldownPanel(drilldown) {
                this.panelStack.pop();
                this.render();
            },

            // ------------------------------------------------------------------------ panel events
            /** event map */
            events: {
                "click .navigation .back": "close"
            },

            /** close/remove this collection panel */
            close: function close(event) {
                this.remove();
                this.trigger("close");
            },

            // ........................................................................ misc
            /** string rep */
            toString: function toString() {
                return "CollectionView(" + (this.model ? this.model.get("name") : "") + ")";
            }
        });

    //------------------------------------------------------------------------------ TEMPLATES
    CollectionView.prototype.templates = function() {
        var controlsTemplate = function controlsTemplate(collection, view) {
            var subtitle = collectionDescription(view.model);
            return "\n        <div class=\"controls\">\n            <div class=\"navigation\">\n            <a class=\"back\" href=\"javascript:void(0)\">\n                <span class=\"fa fa-icon fa-angle-left\"></span>\n                " + (0, _localization2.default)("Back to ") + "\n                " + _.escape(view.parentName) + "\n            </a>\n            </div>\n            <div class=\"title\">\n                <div class=\"name\">" + (_.escape(collection.name) || _.escape(collection.element_identifier)) + "</div>\n                <div class=\"subtitle\">\n                    " + subtitle + "\n                </div>\n            </div>\n            <div class=\"elements-warning\">\n            </div>\n            <div class=\"tags-display\"></div>\n            <div class=\"actions\">\n                <a class=\"download-btn icon-btn\" href=\"" + view.downloadUrl + "\"\n                   title=\"\" download=\"\" data-original-title=\"Download Collection\">\n                   <span class=\"fa fa-floppy-o\"></span>\n                </a>\n            </div>\n        </div>";
        };

        return _.extend(_.clone(_super.prototype.templates), {
            controls: controlsTemplate
        });
    }();

    function collectionTypeDescription(collection) {
        var collectionType = collection.get("collection_type");
        var collectionTypeDescription;
        if (collectionType == "list") {
            collectionTypeDescription = (0, _localization2.default)("list");
        } else if (collectionType == "paired") {
            collectionTypeDescription = (0, _localization2.default)("dataset pair");
        } else if (collectionType == "list:paired") {
            collectionTypeDescription = (0, _localization2.default)("list of pairs");
        } else {
            collectionTypeDescription = (0, _localization2.default)("nested list");
        }
        return collectionTypeDescription;
    }

    function collectionDescription(collection) {
        var elementCount = collection.get("element_count");

        var itemsDescription = "a " + collectionTypeDescription(collection);
        if (elementCount) {
            var countDescription;
            if (elementCount == 1) {
                countDescription = "with 1 item";
            } else if (elementCount) {
                countDescription = "with " + elementCount + " items";
            }
            itemsDescription = itemsDescription + " " + (0, _localization2.default)(countDescription);
        }
        return itemsDescription;
    }

    //==============================================================================
    exports.default = {
        collectionTypeDescription: collectionTypeDescription,
        collectionDescription: collectionDescription,
        CollectionView: CollectionView
    };
});
//# sourceMappingURL=../../../maps/mvc/collection/collection-view.js.map
