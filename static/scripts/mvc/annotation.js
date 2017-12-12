define("mvc/annotation", ["exports", "mvc/base-mvc", "utils/localization", "ui/editable-text"], function(exports, _baseMvc, _localization) {
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
    /** A view on any model that has a 'annotation' attribute
     */
    var AnnotationEditor = Backbone.View.extend(_baseMvc2.default.LoggableMixin).extend(_baseMvc2.default.HiddenUntilActivatedViewMixin).extend({
        tagName: "div",
        className: "annotation-display",

        /** Set up listeners, parse options */
        initialize: function initialize(options) {
            options = options || {};
            this.tooltipConfig = options.tooltipConfig || {
                placement: "bottom"
            };
            //console.debug( this, options );
            // only listen to the model only for changes to annotations
            this.listenTo(this.model, "change:annotation", function() {
                this.render();
            });
            this.hiddenUntilActivated(options.$activator, options);
        },

        /** Build the DOM elements, call select to on the created input, and set up behaviors */
        render: function render() {
            var view = this;
            this.$el.html(this._template());

            //TODO: handle empties better
            this.$annotation().make_text_editable({
                use_textarea: true,
                on_finish: function on_finish(newAnnotation) {
                    view.$annotation().text(newAnnotation);
                    view.model.save({
                        annotation: newAnnotation
                    }, {
                        silent: true
                    }).fail(function() {
                        view.$annotation().text(view.model.previous("annotation"));
                    });
                }
            });
            return this;
        },

        /** @returns {String} the html text used to build the view's DOM */
        _template: function _template() {
            var annotation = this.model.get("annotation");
            return [
                //TODO: make prompt optional
                '<label class="prompt">', (0, _localization2.default)("Annotation"), "</label>",
                // set up initial tags by adding as CSV to input vals (necc. to init select2)
                '<div class="annotation">', _.escape(annotation), "</div>"
            ].join("");
        },

        /** @returns {jQuery} the main element for this view */
        $annotation: function $annotation() {
            return this.$el.find(".annotation");
        },

        /** shut down event listeners and remove this view's DOM */
        remove: function remove() {
            this.$annotation.off();
            this.stopListening(this.model);
            Backbone.View.prototype.remove.call(this);
        },

        /** string rep */
        toString: function toString() {
            return ["AnnotationEditor(", "" + this.model, ")"].join("");
        }
    });
    // =============================================================================
    exports.default = {
        AnnotationEditor: AnnotationEditor
    };
});
//# sourceMappingURL=../../maps/mvc/annotation.js.map
