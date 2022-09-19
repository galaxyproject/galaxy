import _ from "underscore";
import { getAppRoot } from "onload/loadConfig";
import LIST_VIEW from "mvc/list/list-view";
import DC_LI from "mvc/collection/collection-li";
import _l from "utils/localization";

var logNamespace = "collections";
/* =============================================================================
TODO:

============================================================================= */
/** @class non-editable, read-only View/Controller for a dataset collection.
 */
var _super = LIST_VIEW.ModelListPanel;
var CollectionView = _super.extend(
    /** @lends CollectionView.prototype */ {
        //MODEL is either a DatasetCollection (or subclass) or a DatasetCollectionElement (list of pairs)
        _logNamespace: logNamespace,

        className: `${_super.prototype.className} dataset-collection-panel`,

        /** sub view class used for datasets */
        DatasetDCEViewClass: DC_LI.DatasetDCEListItemView,

        /** key of attribute in model to assign to this.collection */
        modelCollectionKey: "elements",

        // ......................................................................... SET UP
        /** Set up the view, set up storage, bind listeners to HistoryContents events
         *  @param {Object} attributes optional settings for the panel
         */
        initialize: function (attributes) {
            _super.prototype.initialize.call(this, attributes);
            this.linkTarget = attributes.linkTarget || "_blank";
            this.dragItems = true;
            this.hasUser = attributes.hasUser;
            /** A stack of panels that currently cover or hide this panel */
            this.panelStack = [];
            /** The text of the link to go back to the panel containing this one */
            this.parentName = attributes.parentName;
            /** foldout or drilldown */
            this.foldoutStyle = attributes.foldoutStyle || "foldout";
            this.downloadUrl = `${getAppRoot()}api/dataset_collections/${this.model.attributes.id}/download`;
        },

        getNestedDCDCEViewClass: function () {
            return DC_LI.NestedDCDCEListItemView.extend({
                foldoutPanelClass: CollectionView,
            });
        },

        _queueNewRender: function ($newRender, speed) {
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

        handleWarning: function ($newRender) {
            var $warns = $newRender.find(".elements-warning");
            if (this.model.get("populated_state") === "failed") {
                var error = _l(`${this.model.get("populated_state_message")}`);
                $warns.html(`<div class="errormessagesmall">${error}</div>`);
                return;
            }
            var viewLength = this.views.length;
            var elementCount = this.model.get("element_count");
            if (elementCount && elementCount !== viewLength) {
                var warning = _l(`displaying only ${viewLength} of ${elementCount} items`);
                $warns.html(`<div class="warningmessagesmall">${warning}</div>`);
            }
        },

        // ------------------------------------------------------------------------ sub-views
        /** In this override, use model.getVisibleContents */
        _filterCollection: function () {
            //TODO: should *not* be model.getVisibleContents - visibility is not model related
            return this.model.getVisibleContents();
        },

        /** override to return proper view class based on element_type */
        _getItemViewClass: function (model) {
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
        _getItemViewOptions: function (model) {
            var options = _super.prototype._getItemViewOptions.call(this, model);
            return _.extend(options, {
                linkTarget: this.linkTarget,
                hasUser: this.hasUser,
                //TODO: could move to only nested: list:paired
                foldoutStyle: this.foldoutStyle,
            });
        },

        // ------------------------------------------------------------------------ collection sub-views
        /** In this override, add/remove expanded/collapsed model ids to/from web storage */
        _setUpItemViewListeners: function (view) {
            var panel = this;
            _super.prototype._setUpItemViewListeners.call(panel, view);

            // use pub-sub to: handle drilldown expansion and collapse
            panel.listenTo(view, {
                "expanded:drilldown": function (v, drilldown) {
                    this._expandDrilldownPanel(drilldown);
                },
                "collapsed:drilldown": function (v, drilldown) {
                    this._collapseDrilldownPanel(drilldown);
                },
            });
            return this;
        },

        /** Handle drill down by hiding this panels list and controls and showing the sub-panel */
        _expandDrilldownPanel: function (drilldown) {
            this.panelStack.push(drilldown);
            // hide this panel's controls and list, set the name for back navigation, and attach to the $el
            this.$("> .controls").add(this.$list()).hide();
            drilldown.parentName = this.model.get("name");
            this.$el.append(drilldown.render().$el);
        },

        /** Handle drilldown close by freeing the panel and re-rendering this panel */
        _collapseDrilldownPanel: function (drilldown) {
            this.panelStack.pop();
            this.render();
        },

        // ------------------------------------------------------------------------ panel events
        /** event map */
        events: {
            "click .navigation .back": "close",
        },

        /** close/remove this collection panel */
        close: function (event) {
            this.remove();
            this.trigger("close");
        },

        // ........................................................................ misc
        /** string rep */
        toString: function () {
            return `CollectionView(${this.model ? this.model.get("name") : ""})`;
        },
    }
);

//------------------------------------------------------------------------------ TEMPLATES
CollectionView.prototype.templates = (() => {
    var controlsTemplate = (collection, view) => {
        var subtitle = collectionDescription(view.model);
        return `
        <div class="controls">
            <div class="navigation">
            <a class="back" href="javascript:void(0)">
                <span class="fa fa-icon fa-angle-left"></span>
                ${_l("Back to ")}
                ${_.escape(view.parentName)}
            </a>
            </div>
            <div class="title">
                <div class="name">${_.escape(collection.name) || _.escape(collection.element_identifier)}</div>
                <div class="subtitle">
                    ${subtitle}
                </div>
            </div>
            <div class="elements-warning">
            </div>
            <div class="tags-display"></div>
            <div class="actions">
                <a class="download-btn icon-btn" href="${view.downloadUrl}"
                   title="" download="" data-original-title="Download Collection">
                   <span class="fa fa-floppy-o"></span>
                </a>
            </div>
        </div>`;
    };

    return _.extend(_.clone(_super.prototype.templates), {
        controls: controlsTemplate,
    });
})();

function collectionTypeDescription(collection) {
    var collectionType = collection.get("collection_type");
    var collectionTypeDescription;
    if (collectionType == "list") {
        collectionTypeDescription = _l("list");
    } else if (collectionType == "paired") {
        collectionTypeDescription = _l("dataset pair");
    } else if (collectionType == "list:paired") {
        collectionTypeDescription = _l("list of pairs");
    } else {
        collectionTypeDescription = _l("nested list");
    }
    return collectionTypeDescription;
}

function collectionDescription(collection) {
    var elementCount = collection.get("element_count");

    var itemsDescription = `a ${collectionTypeDescription(collection)}`;
    if (elementCount) {
        var countDescription;
        if (elementCount == 1) {
            countDescription = "with 1 item";
        } else if (elementCount) {
            countDescription = `with ${elementCount} items`;
        }
        itemsDescription = `${itemsDescription} ${_l(countDescription)}`;
    }
    return itemsDescription;
}

//==============================================================================
export default {
    collectionTypeDescription: collectionTypeDescription,
    collectionDescription: collectionDescription,
    CollectionView: CollectionView,
};
