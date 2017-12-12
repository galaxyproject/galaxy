define("mvc/tag", ["exports", "mvc/base-mvc", "utils/localization"], function(exports, _baseMvc, _localization) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });

    var _baseMvc2 = _interopRequireDefault(_baseMvc);

    var _localization2 = _interopRequireDefault(_localization);

    function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : {
            default: obj
        };
    }

    // =============================================================================
    /** A view on any model that has a 'tags' attribute (a list of tag strings)
     *      Incorporates the select2 jQuery plugin for tags display/editing:
     *      http://ivaynberg.github.io/select2/
     */
    var TagsEditor = Backbone.View.extend(_baseMvc2.default.LoggableMixin).extend(_baseMvc2.default.HiddenUntilActivatedViewMixin).extend({
        tagName: "div",
        className: "tags-display",
        select_width: "100%",
        events: {},

        /** Set up listeners, parse options */
        initialize: function initialize(options) {
            //console.debug( this, options );
            // only listen to the model only for changes to tags - re-render
            this.show_editor = false;
            if (options.usePrompt === false) {
                this.label = "";
            } else {
                this.label = "<label class=\"prompt\">" + (0, _localization2.default)("Tags") + "</label>";
            }
            this.workflow_mode = options.workflow_mode || false;
            if (this.workflow_mode) {
                this.events.click = "showEditor";
                this.events.keydown = "keydownHandler";
            }
            this.hiddenUntilActivated(options.$activator, options);
        },

        /** Build the DOM elements, call select to on the created input, and set up behaviors */
        render: function render() {
            var self = this;
            if (this.workflow_mode) {
                this.$el.html(this._workflowTemplate());
            } else {
                this.$el.html(this._defaultTemplate());
            }
            this.$input().select2({
                placeholder: "Add tags",
                width: this.workflow_mode ? this.width : this.select_width,
                tags: function tags() {
                    // initialize possible tags in the dropdown based on all the tags the user has used so far
                    return self._getTagsUsed();
                }
            });

            this._setUpBehaviors();
            return this;
        },

        _hashToName: function _hashToName(tag) {
            if (tag.startsWith("#")) {
                return "name:" + tag.slice(1);
            }
            return tag;
        },

        _nameToHash: function _nameToHash(tag) {
            if (tag.startsWith("name:")) {
                tag = "#" + tag.slice(5);
            }
            return tag;
        },

        /** @returns {String} the html text used to build the view's DOM */
        _defaultTemplate: function _defaultTemplate() {
            return [this.label, this._renderEditor()].join("");
        },

        _workflowTemplate: function _workflowTemplate() {
            // Shows labels by default, event handler controls whether we show tags or editor
            return [this.show_editor ? this._renderEditor() : this._renderTags()].join(" ");
        },

        keydownHandler: function keydownHandler(e) {
            switch (e.which) {
                // esc
                case 27:
                    // hide the tag editor when pressing escape
                    this.hideEditor();
                    break;
            }
        },

        showEditor: function showEditor() {
            this.show_editor = true;
            this.render();
        },

        hideEditor: function hideEditor() {
            this.show_editor = false;
            this.render();
        },

        _renderEditor: function _renderEditor() {
            // set up initial tags by adding as CSV to input vals (necc. to init select2)
            return "<input class=\"tags-input\" value=\"" + this.tagsToCSV() + "\"/>";
        },

        _renderTags: function _renderTags() {
            var tags = this.model.get("tags");
            var addButton = Galaxy.root + "static/images/fugue/tag--plus.png";
            var renderedArray = [];
            _.each(tags, function(tag) {
                tag = tag.indexOf("name:") == 0 ? tag.slice(5) : tag;
                var renderString = "<span class=\"label label-info\">" + tag + "</span>";
                renderedArray.push(renderString);
            });
            if (renderedArray.length === 0) {
                // If there are no tags to render we just show the add-tag-button
                renderedArray.push("<img src=" + addButton + " class=\"add-tag-button\" title=\"Add tags\"/>");
            }
            return renderedArray.join(" ");
        },

        /** @returns {String} the sorted, comma-separated tags from the model */
        tagsToCSV: function tagsToCSV() {
            var self = this;
            var tagsArray = this.model.get("tags");
            if (!_.isArray(tagsArray) || _.isEmpty(tagsArray)) {
                return "";
            }
            return tagsArray.map(function(tag) {
                return _.escape(self._nameToHash(tag));
            }).sort().join(",");
        },

        /** @returns {jQuery} the input for this view */
        $input: function $input() {
            return this.$el.find("input.tags-input");
        },

        /** @returns {String[]} all tags used by the current user */
        _getTagsUsed: function _getTagsUsed() {
            //TODO: global
            var self = this;
            return _.map(Galaxy.user.get("tags_used"), self._nameToHash);
        },

        /** set up any event listeners on the view's DOM (mostly handled by select2) */
        _setUpBehaviors: function _setUpBehaviors() {
            var self = this;
            this.$input().on("change", function(event) {
                // Modify any 'hashtag' 'nametags'
                event.val = _.map(event.val, self._hashToName);
                // save the model's tags in either remove or added event
                self.model.save({
                    tags: event.val
                });
                // if it's new, add the tag to the users tags
                if (event.added) {
                    //??: solve weird behavior in FF on test.galaxyproject.org where
                    //  event.added.text is string object: 'String{ 0="o", 1="n", 2="e" }'
                    self._addNewTagToTagsUsed("" + event.added.text);
                }
            });
        },

        /** add a new tag (if not already there) to the list of all tags used by the user
         *  @param {String} newTag  the tag to add to the list of used
         */
        _addNewTagToTagsUsed: function _addNewTagToTagsUsed(newTag) {
            //TODO: global
            var tagsUsed = Galaxy.user.get("tags_used");
            if (!_.contains(tagsUsed, newTag)) {
                tagsUsed.push(newTag);
                tagsUsed.sort();
                Galaxy.user.set("tags_used", tagsUsed);
            }
        },

        /** shut down event listeners and remove this view's DOM */
        remove: function remove() {
            this.$input.off();
            this.stopListening(this.model);
            Backbone.View.prototype.remove.call(this);
        },

        /** string rep */
        toString: function toString() {
            return ["TagsEditor(", "" + this.model, ")"].join("");
        }
    });

    exports.default = {
        TagsEditor: TagsEditor
    };
});
//# sourceMappingURL=../../maps/mvc/tag.js.map
