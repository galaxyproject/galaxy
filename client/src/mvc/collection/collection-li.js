import _ from "underscore";
import $ from "jquery";
import { ListItemView, FoldoutListItemView } from "mvc/list/list-item";
import { DatasetListItemView } from "mvc/dataset/dataset-li";
import BASE_MVC from "mvc/base-mvc";
import _l from "utils/localization";

/** @class Read only view for DatasetCollection.
 */
var DCListItemView = FoldoutListItemView.extend(
    /** @lends DCListItemView.prototype */ {
        className: `${FoldoutListItemView.prototype.className} dataset-collection`,
        id: function () {
            return ["dataset_collection", this.model.get("id")].join("-");
        },

        /** override to add linkTarget */
        initialize: function (attributes) {
            this.linkTarget = attributes.linkTarget || "_blank";
            this.hasUser = attributes.hasUser;
            FoldoutListItemView.prototype.initialize.call(this, attributes);
        },

        /** event listeners */
        _setUpListeners: function () {
            FoldoutListItemView.prototype._setUpListeners.call(this);
            this.listenTo(this.model, "change", function (model, options) {
                // if the model has changed deletion status render it entirely
                if (_.has(model.changed, "deleted")) {
                    this.render();

                    // if the model has been decorated after the fact with the element count,
                    // render the subtitle where the count is displayed
                } else if (_.has(model.changed, "element_count")) {
                    this.$("> .title-bar .subtitle").replaceWith(this._renderSubtitle());
                }
            });
        },

        // ......................................................................... rendering
        /** render a subtitle to show the user what sort of collection this is */
        _renderSubtitle: function () {
            return $(this.templates.subtitle(this.model.toJSON(), this));
        },

        // ......................................................................... foldout
        /** override to add linktarget to sub-panel */
        _getFoldoutPanelOptions: function () {
            var options = FoldoutListItemView.prototype._getFoldoutPanelOptions.call(this);
            return _.extend(options, {
                linkTarget: this.linkTarget,
                hasUser: this.hasUser,
            });
        },

        /** override to not catch sub-panel selectors */
        $selector: function () {
            return this.$("> .selector");
        },

        // ......................................................................... misc
        /** String representation */
        toString: function () {
            var modelString = this.model ? `${this.model}` : "(no model)";
            return `DCListItemView(${modelString})`;
        },
    }
);

// ............................................................................ TEMPLATES
/** underscore templates */
DCListItemView.prototype.templates = (() => {
    var warnings = _.extend({}, FoldoutListItemView.prototype.templates.warnings, {
        error: BASE_MVC.wrapTemplate([
            // error during index fetch - show error on dataset
            "<% if( model.error ){ %>",
            '<div class="errormessagesmall">',
            _l("There was an error getting the data for this collection"),
            ": <%- model.error %>",
            "</div>",
            "<% } %>",
        ]),
        purged: BASE_MVC.wrapTemplate([
            "<% if( model.purged ){ %>",
            '<div class="purged-msg warningmessagesmall">',
            _l("This collection has been deleted and removed from disk"),
            "</div>",
            "<% } %>",
        ]),
        deleted: BASE_MVC.wrapTemplate([
            // deleted not purged
            "<% if( model.deleted && !model.purged ){ %>",
            '<div class="deleted-msg warningmessagesmall">',
            _l("This collection has been deleted"),
            "</div>",
            "<% } %>",
        ]),
    });

    // use element identifier
    var titleBarTemplate = BASE_MVC.wrapTemplate(
        [
            '<div class="title-bar clear" tabindex="0">',
            '<div class="title">',
            '<span class="name"><%- collection.element_identifier || collection.name %></span>',
            "</div>",
            '<div class="subtitle"></div>',
            "</div>",
        ],
        "collection"
    );

    // use element identifier
    var subtitleTemplate = BASE_MVC.wrapTemplate(
        [
            '<div class="subtitle">',
            '<% var countText = collection.element_count? ( collection.element_count + " " ) : ""; %>',
            '<%        if( collection.collection_type === "list" ){ %>',
            _l("a list of <%- countText %>datasets"),
            '<% } else if( collection.collection_type === "paired" ){ %>',
            _l("a pair of datasets"),
            '<% } else if( collection.collection_type === "list:paired" ){ %>',
            _l("a list of <%- countText %>dataset pairs"),
            '<% } else if( collection.collection_type === "list:list" ){ %>',
            _l("a list of <%- countText %>dataset lists"),
            "<% } %>",
            "</div>",
        ],
        "collection"
    );

    return _.extend({}, FoldoutListItemView.prototype.templates, {
        warnings: warnings,
        titleBar: titleBarTemplate,
        subtitle: subtitleTemplate,
    });
})();

//==============================================================================
/** @class Read only view for DatasetCollectionElement.
 */
var DCEListItemView = ListItemView.extend(
    /** @lends DCEListItemView.prototype */ {
        /** add the DCE class to the list item */
        className: `${ListItemView.prototype.className} dataset-collection-element`,

        /** set up */
        initialize: function (attributes) {
            if (attributes.logger) {
                this.logger = this.model.logger = attributes.logger;
            }
            this.log("DCEListItemView.initialize:", attributes);
            ListItemView.prototype.initialize.call(this, attributes);
        },

        // ......................................................................... misc
        /** String representation */
        toString: function () {
            var modelString = this.model ? `${this.model}` : "(no model)";
            return `DCEListItemView(${modelString})`;
        },
    }
);

// ............................................................................ TEMPLATES
/** underscore templates */
DCEListItemView.prototype.templates = (() => {
    // use the element identifier here - since that will persist and the user will need it
    var titleBarTemplate = BASE_MVC.wrapTemplate(
        [
            '<div class="title-bar clear" tabindex="0">',
            '<div class="title">',
            '<span class="name"><%- element.element_identifier %></span>',
            "</div>",
            '<div class="subtitle"></div>',
            "</div>",
        ],
        "element"
    );

    return _.extend({}, ListItemView.prototype.templates, {
        titleBar: titleBarTemplate,
    });
})();

//==============================================================================
/** @class Read only view for a DatasetCollectionElement that is also an DatasetAssociation
 *      (a dataset contained in a dataset collection).
 */
var DatasetDCEListItemView = DatasetListItemView.extend(
    /** @lends DatasetDCEListItemView.prototype */ {
        className: `${DatasetListItemView.prototype.className} dataset-collection-element`,

        /** set up */
        initialize: function (attributes) {
            if (attributes.logger) {
                this.logger = this.model.logger = attributes.logger;
            }
            this.log("DatasetDCEListItemView.initialize:", attributes);
            DatasetListItemView.prototype.initialize.call(this, attributes);
        },

        /** In this override, only get details if in the ready state.
         *  Note: fetch with no 'change' event triggering to prevent automatic rendering.
         */
        _fetchModelDetails: function () {
            var view = this;
            if (view.model.inReadyState() && !view.model.hasDetails()) {
                return view.model.fetch({ silent: true });
            }
            return $.when();
        },

        // ......................................................................... misc
        /** String representation */
        toString: function () {
            var modelString = this.model ? `${this.model}` : "(no model)";
            return `DatasetDCEListItemView(${modelString})`;
        },
    }
);

// ............................................................................ TEMPLATES
/** underscore templates */
DatasetDCEListItemView.prototype.templates = (() => {
    // use the element identifier here and not the dataset name
    //TODO:?? can we steal the DCE titlebar?
    var titleBarTemplate = BASE_MVC.wrapTemplate(
        [
            '<div class="title-bar clear" tabindex="0">',
            '<span class="state-icon"></span>',
            '<div class="title">',
            '<span class="name"><%- element.element_identifier %></span>',
            "</div>",
            "</div>",
        ],
        "element"
    );

    return _.extend({}, DatasetListItemView.prototype.templates, {
        titleBar: titleBarTemplate,
    });
})();

//==============================================================================
/** @class Read only view for a DatasetCollectionElement that is also a DatasetCollection
 *      (a nested DC).
 */
var NestedDCDCEListItemView = DCListItemView.extend(
    /** @lends NestedDCDCEListItemView.prototype */ {
        className: `${DCListItemView.prototype.className} dataset-collection-element`,

        /** In this override, add the state as a class for use with state-based CSS */
        _swapNewRender: function ($newRender) {
            DCListItemView.prototype._swapNewRender.call(this, $newRender);
            var state = this.model.get("state") || "ok";
            this.$el.addClass(`state-${state}`);
            this.$el.attr("data-state", state);
            return this.$el;
        },

        // ......................................................................... misc
        /** String representation */
        toString: function () {
            var modelString = this.model ? `${this.model}` : "(no model)";
            return `NestedDCDCEListItemView(${modelString})`;
        },
    }
);

//==============================================================================
export default {
    DCListItemView: DCListItemView,
    DCEListItemView: DCEListItemView,
    DatasetDCEListItemView: DatasetDCEListItemView,
    NestedDCDCEListItemView: NestedDCDCEListItemView,
};
