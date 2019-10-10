import _ from "underscore";
import Backbone from "backbone";
import { getAppRoot } from "onload/loadConfig";
import { getGalaxyInstance } from "app";
import baseMVC from "mvc/base-mvc";
import _l from "utils/localization";

// =============================================================================
/** A view on any model that has a 'tags' attribute (a list of tag strings)
 *      Incorporates the select2 jQuery plugin for tags display/editing:
 *      http://ivaynberg.github.io/select2/
 */
var TagsEditor = Backbone.View.extend(baseMVC.LoggableMixin)
    .extend(baseMVC.HiddenUntilActivatedViewMixin)
    .extend({
        tagName: "div",
        className: "tags-display",
        select_width: "100%",
        events: {},

        /** Set up listeners, parse options */
        initialize: function(options) {
            //console.debug( this, options );
            // only listen to the model only for changes to tags - re-render
            this.show_editor = false;
            if (options.usePrompt === false) {
                this.label = "";
            } else {
                this.label = `<label class="prompt">${_l("Tags")}</label>`;
            }
            this.workflow_mode = options.workflow_mode || false;
            if (this.workflow_mode) {
                this.events.click = "showEditor";
                this.events.keydown = "keydownHandler";
            }
            this.hiddenUntilActivated(options.$activator, options);
        },

        /** Build the DOM elements, call select to on the created input, and set up behaviors */
        render: function() {
            var self = this;
            if (this.workflow_mode) {
                this.$el.html(this._workflowTemplate());
            } else {
                this.$el.html(this._defaultTemplate());
            }
            this.$input().select2({
                placeholder: "Add tags",
                width: this.workflow_mode ? this.width : this.select_width,
                tags: function() {
                    // initialize possible tags in the dropdown based on all the tags the user has used so far
                    return self._getTagsUsed();
                }
            });

            this._setUpBehaviors();
            return this;
        },

        _hashToName: function(tag) {
            if (tag.startsWith("#")) {
                return `name:${tag.slice(1)}`;
            }
            return tag;
        },

        _nameToHash: function(tag) {
            if (tag.startsWith("name:")) {
                tag = `#${tag.slice(5)}`;
            }
            return tag;
        },

        /** @returns {String} the html text used to build the view's DOM */
        _defaultTemplate: function() {
            return [this.label, this._renderEditor()].join("");
        },

        _workflowTemplate: function() {
            // Shows labels by default, event handler controls whether we show tags or editor
            return [this.show_editor ? this._renderEditor() : this._renderTags()].join(" ");
        },

        keydownHandler: function(e) {
            switch (e.which) {
                // esc
                case 27:
                    // hide the tag editor when pressing escape
                    this.hideEditor();
                    break;
            }
        },

        showEditor: function() {
            this.show_editor = true;
            this.render();
        },

        hideEditor: function() {
            this.show_editor = false;
            this.render();
        },

        _renderEditor: function() {
            // set up initial tags by adding as CSV to input vals (necc. to init select2)
            return `<input class="tags-input" value="${this.tagsToCSV()}"/>`;
        },

        _renderTags: function() {
            var tags = this.model.get("tags");
            var addButton = `${getAppRoot()}static/images/fugue/tag--plus.png`;
            var renderedArray = [];
            _.each(tags, tag => {
                tag = tag.indexOf("name:") == 0 ? tag.slice(5) : tag;
                var renderString = `<span class="badge badge-primary badge-tags">${tag}</span>`;
                renderedArray.push(renderString);
            });
            if (renderedArray.length === 0) {
                // If there are no tags to render we just show the add-tag-button
                renderedArray.push(`<img src=${addButton} class="add-tag-button" title="Add tags"/>`);
            }
            return renderedArray.join(" ");
        },

        /** @returns {String} the sorted, comma-separated tags from the model */
        tagsToCSV: function() {
            var self = this;
            var tagsArray = this.model.get("tags");
            if (!_.isArray(tagsArray) || _.isEmpty(tagsArray)) {
                return "";
            }
            return tagsArray
                .map(tag => _.escape(self._nameToHash(tag)))
                .sort()
                .join(",");
        },

        /** @returns {jQuery} the input for this view */
        $input: function() {
            return this.$el.find("input.tags-input");
        },

        /** @returns {String[]} all tags used by the current user */
        _getTagsUsed: function() {
            let Galaxy = getGalaxyInstance();
            var self = this;
            return _.map(Galaxy.user.get("tags_used"), self._nameToHash);
        },

        /** set up any event listeners on the view's DOM (mostly handled by select2) */
        _setUpBehaviors: function() {
            var self = this;
            this.$input().on("change", event => {
                // Modify any 'hashtag' 'nametags'
                event.val = _.map(event.val, self._hashToName);
                // save the model's tags in either remove or added event
                self.model.save({ tags: event.val });
                // if it's new, add the tag to the users tags
                if (event.added) {
                    //??: solve weird behavior in FF on test.galaxyproject.org where
                    //  event.added.text is string object: 'String{ 0="o", 1="n", 2="e" }'
                    self._addNewTagToTagsUsed(`${event.added.text}`);
                }
            });
        },

        /** add a new tag (if not already there) to the list of all tags used by the user
         *  @param {String} newTag  the tag to add to the list of used
         */
        _addNewTagToTagsUsed: function(newTag) {
            let Galaxy = getGalaxyInstance();
            var tagsUsed = Galaxy.user.get("tags_used");
            if (!_.contains(tagsUsed, newTag)) {
                tagsUsed.push(newTag);
                tagsUsed.sort();
                Galaxy.user.set("tags_used", tagsUsed);
            }
        },

        /** shut down event listeners and remove this view's DOM */
        remove: function() {
            this.$input.off();
            this.stopListening(this.model);
            Backbone.View.prototype.remove.call(this);
        },

        /** string rep */
        toString: function() {
            return ["TagsEditor(", `${this.model}`, ")"].join("");
        }
    });

export default {
    TagsEditor: TagsEditor
};
