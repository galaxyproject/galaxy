define("mvc/ui/ui-popover", ["exports", "utils/utils"], function(exports, _utils) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });

    var _utils2 = _interopRequireDefault(_utils);

    function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : {
            default: obj
        };
    }

    var View = Backbone.View.extend({
        optionsDefault: {
            with_close: true,
            title: null,
            placement: "top",
            container: "body",
            body: null
        },

        initialize: function initialize(options) {
            this.setElement(this._template());
            this.uid = _utils2.default.uid();
            this.options = _.defaults(options || {}, this.optionsDefault);
            this.options.container.parent().append(this.el);
            this.$title = this.$(".popover-title-label");
            this.$close = this.$(".popover-close");
            this.$body = this.$(".popover-content");

            // add initial content
            this.options.body && this.append(this.options.body);

            // add event to hide if click is outside of popup and not on container
            var self = this;
            $("body").on("mousedown." + this.uid, function(e) {
                // the 'is' for buttons that trigger popups
                // the 'has' for icons within a button that triggers a popup
                self.visible && !$(self.options.container).is(e.target) && !$(self.el).is(e.target) && $(self.el).has(e.target).length === 0 && self.hide();
            });
        },

        /**
         * Render popover
         */
        render: function render() {
            this.$title.html(this.options.title);
            this.$el.removeClass().addClass("ui-popover popover fade in").addClass(this.options.placement);
            this.$el.css(this._get_placement(this.options.placement));

            // configure close option
            var self = this;
            if (this.options.with_close) {
                this.$close.on("click", function() {
                    self.hide();
                }).show();
            } else {
                this.$close.off().hide();
            }
        },

        /**
         * Set the popover title
         * @params{ String }    newTitle    - New popover title
         */
        title: function title(newTitle) {
            if (newTitle !== undefined) {
                this.options.title = newTitle;
                this.$title.html(newTitle);
            }
        },

        /**
         * Show popover
         */
        show: function show() {
            this.render();
            this.$el.show();
            this.visible = true;
        },

        /**
         * Hide popover
         */
        hide: function hide() {
            this.$el.hide();
            this.visible = false;
        },

        /**
         * Append new content to the popover
         * @params{ Object }  $el - Dom element
         */
        append: function append($el) {
            this.$body.append($el);
        },

        /**
         * Remove all content
         */
        empty: function empty() {
            this.$body.empty();
        },

        /**
         * Remove popover
         */
        remove: function remove() {
            $("body").off("mousedown." + this.uid);
            this.$el.remove();
        },

        /**
         * Improve popover location/placement
         */
        _get_placement: function _get_placement(placement) {
            // get popover dimensions
            var width = this._get_width(this.$el);
            var height = this.$el.height();

            // get container details
            var $container = this.options.container;
            var container_width = this._get_width($container);
            var container_height = this._get_height($container);
            var container_position = $container.position();

            // get position
            var top;

            var left;
            top = left = 0;
            if (["top", "bottom"].indexOf(placement) != -1) {
                left = container_position.left - width + (container_width + width) / 2;
                switch (placement) {
                    case "top":
                        top = container_position.top - height - 5;
                        break;
                    case "bottom":
                        top = container_position.top + container_height + 5;
                        break;
                }
            } else {
                top = container_position.top - height + (container_height + height) / 2;
                switch (placement) {
                    case "right":
                        left = container_position.left + container_width;
                        break;
                }
            }
            return {
                top: top,
                left: left
            };
        },

        /**
         * Returns padding/margin corrected width
         */
        _get_width: function _get_width($el) {
            return $el.width() + parseInt($el.css("padding-left")) + parseInt($el.css("margin-left")) + parseInt($el.css("padding-right")) + parseInt($el.css("margin-right"));
        },

        /**
         * Returns padding corrected height
         */
        _get_height: function _get_height($el) {
            return $el.height() + parseInt($el.css("padding-top")) + parseInt($el.css("padding-bottom"));
        },

        /**
         * Return the popover template
         */
        _template: function _template(options) {
            return '<div class="ui-popover popover fade in">' + '<div class="arrow"/>' + '<div class="popover-title">' + '<div class="popover-title-label"/>' + '<div class="popover-close fa fa-times-circle"/>' + "</div>" + '<div class="popover-content"/>' + "</div>";
        }
    });
    /**
     * Popover wrapper
     */
    exports.default = {
        View: View
    };
});
//# sourceMappingURL=../../../maps/mvc/ui/ui-popover.js.map
