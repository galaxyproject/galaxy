import _ from "underscore";
import LIST_ITEM from "mvc/list/list-item";
import DATASET_LIST from "mvc/dataset/dataset-list";
import BASE_MVC from "mvc/base-mvc";
import _l from "utils/localization";
//==============================================================================
var _super = LIST_ITEM.FoldoutListItemView;
/** @class A job view used from within a larger list of jobs.
 *      Each job itself is a foldout panel of history contents displaying the outputs of this job.
 */
var JobListItemView = _super.extend(
    /** @lends JobListItemView.prototype */ {
        /** logger used to record this.log messages, commonly set to console */
        //logger              : console,

        className: `${_super.prototype.className} job`,
        id: function() {
            return ["job", this.model.get("id")].join("-");
        },

        foldoutPanelClass: DATASET_LIST.DatasetList,

        /** Set up: instance vars, options, and event handlers */
        initialize: function(attributes) {
            if (attributes.logger) {
                this.logger = this.model.logger = attributes.logger;
            }
            this.log(`${this}.initialize:`, attributes);
            _super.prototype.initialize.call(this, attributes);

            this.tool = attributes.tool || {};
            this.jobData = attributes.jobData || {};

            /** where should pages from links be displayed? (default to new tab/window) */
            this.linkTarget = attributes.linkTarget || "_blank";
        },

        /** In this override, add the state as a class for use with state-based CSS */
        _swapNewRender: function($newRender) {
            _super.prototype._swapNewRender.call(this, $newRender);
            if (this.model.has("state")) {
                this.$el.addClass(`state-${this.model.get("state")}`);
            }
            return this.$el;
        },

        /** Stub to return proper foldout panel options */
        _getFoldoutPanelOptions: function() {
            var options = _super.prototype._getFoldoutPanelOptions.call(this);
            return _.extend(options, {
                collection: this.model.outputCollection,
                selecting: false
            });
        },

        // ........................................................................ template helpers
        // all of these are ADAPTERs - in other words, it might be better if the API returned the final form
        //  or something similar in order to remove some of the complexity here

        /** Return tool.inputs that should/can be safely displayed */
        _labelParamMap: function() {
            //ADAPTER
            var params = this.model.get("params");

            var labelParamMap = {};
            _.each(this.tool.inputs, i => {
                //console.debug( i.label, i.model_class );
                if (i.label && i.model_class !== "DataToolParameter") {
                    labelParamMap[i.label] = params[i.name];
                }
            });
            return labelParamMap;
        },

        _labelInputMap: function() {
            //ADAPTER
            var view = this;

            var labelInputMap = {};
            _.each(this.jobData.inputs, input => {
                var toolInput = view._findToolInput(input.name);
                if (toolInput) {
                    labelInputMap[toolInput.label] = input;
                }
            });
            return labelInputMap;
        },

        /** Return a tool.inputs object that matches (or partially matches) the given (job input) name */
        _findToolInput: function(name) {
            //ADAPTER
            var toolInputs = this.tool.inputs;

            var exactMatch = _.findWhere(toolInputs, { name: name });
            if (exactMatch) {
                return exactMatch;
            }
            return this._findRepeatToolInput(name, toolInputs);
        },

        /** Return a tool.inputs object that partially matches the given (job input) name (for repeat dataset inputs)*/
        _findRepeatToolInput: function(name, toolInputs) {
            //ADAPTER
            toolInputs = toolInputs || this.tool.inputs;
            var partialMatch = _.find(toolInputs, i => name.indexOf(i.name) === 0);
            if (!partialMatch) {
                return undefined;
            }

            var subMatch = _.find(partialMatch.inputs, i => name.indexOf(i.name) !== -1);
            return subMatch;
        },

        // ........................................................................ misc
        /** String representation */
        toString: function() {
            return `JobListItemView(${this.model})`;
        }
    }
);

// ............................................................................ TEMPLATES
/** underscore templates */
JobListItemView.prototype.templates = (() => {
    //TODO: move to require text! plugin

    // TODO: Is this actually used?
    // eslint-disable-next-line no-unused-vars
    var elTemplate = BASE_MVC.wrapTemplate([
        '<div class="list-element">',
        '<div class="id"><%- model.id %></div>',
        // errors, messages, etc.
        '<div class="warnings"></div>',

        // multi-select checkbox
        '<div class="selector">',
        '<span class="fa fa-2x fa-square-o"></span>',
        "</div>",
        // space for title bar buttons - gen. floated to the right
        '<div class="primary-actions"></div>',
        '<div class="title-bar"></div>',

        // expandable area for more details
        '<div class="details"></div>',
        "</div>"
    ]);

    var titleBarTemplate = BASE_MVC.wrapTemplate(
        [
            // adding a tabindex here allows focusing the title bar and the use of keydown to expand the dataset display
            '<div class="title-bar clear" tabindex="0">',
            //'<span class="state-icon"></span>',
            '<div class="title">',
            '<span class="name"><%- view.tool.name %></span>',
            "</div>",
            '<div class="subtitle">',
            '<span class="description"><%- view.tool.description %></span',
            '<span class="create-time">',
            " ",
            _l("Created"),
            ": <%= new Date( job.create_time ).toString() %>, ",
            "</span",
            "</div>",
            "</div>"
        ],
        "job"
    );

    var subtitleTemplate = BASE_MVC.wrapTemplate(
        [
            '<div class="subtitle">',
            '<span class="description"><%- view.tool.description %></span',
            //'<span class="create-time">',
            //    ' ', _l( 'Created' ), ': <%= new Date( job.create_time ).toString() %>, ',
            //'</span',
            //'<span class="version">',
            //    ' (', _l( 'version' ), ': <%- view.tool.version %>)',
            //'</span',
            "</div>"
        ],
        "job"
    );

    var detailsTemplate = BASE_MVC.wrapTemplate(
        [
            '<div class="details">',
            //'<div class="version">',
            //    '<label class="prompt">', _l( 'Version' ), '</label>',
            //    '<span class="value"><%- view.tool.version %></span>',
            //'</div>',
            '<div class="params">',
            "<% _.each( view._labelInputMap(), function( input, label ){ %>",
            '<div class="input" data-input-name="<%- input.name %>" data-input-id="<%- input.id %>">',
            '<label class="prompt"><%- label %></label>',
            //TODO: input dataset name
            '<span class="value"><%- input.content.name %></span>',
            "</div>",
            "<% }) %>",
            "<% _.each( view._labelParamMap(), function( param, label ){ %>",
            '<div class="param" data-input-name="<%- param.name %>">',
            '<label class="prompt"><%- label %></label>',
            '<span class="value"><%- param %></span>',
            "</div>",
            "<% }) %>",
            "</div>",
            "</div>"
        ],
        "job"
    );

    return _.extend({}, _super.prototype.templates, {
        //el          : elTemplate,
        titleBar: titleBarTemplate,
        subtitle: subtitleTemplate,
        details: detailsTemplate
    });
})();

//=============================================================================
export default {
    JobListItemView: JobListItemView
};
