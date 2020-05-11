/**
 * Popover wrapper
 */
import $ from "jquery";
import Backbone from "backbone";
import _ from "underscore";
import Utils from "utils/utils";

export default Backbone.View.extend({
    initialize: function (options) {
        this.options = _.defaults(options || {}, {
            title: null,
            placement: "top",
            container: "body",
        });
        this.uid = Utils.uid();
        this.$target = this.options.container;
    },

    /**
     * Show popover
     */
    show: function ($content) {
        const btn = "<i class='popover-close fa fa-times-circle'/>";
        $(this.$target).popover({
            title: `${this.options.title} ${btn}`,
            placement: this.options.placement,
            content: $content,
            html: true,
            trigger: "manual",
        });
        if (this.options.class) {
            $(this.$target).addClass(this.options.class);
        }
        $(this.$target).popover("show");

        // add event to hide if click is outside of popup and not on container
        var self = this;
        const $popover = $(this.$target.data("bs.popover").tip);
        $popover.find(".popover-header > i").on("click", () => this.hide());
        $("body").on(`mousedown.${this.uid}`, (e) => {
            if (!$($popover).is(e.target) && $($popover).has(e.target).length === 0) {
                self.hide();
            }
        });
    },

    /**
     * Hide popover
     */
    hide: function () {
        $(this.$target).popover("dispose");
        $("body").off(`mousedown.${this.uid}`);
    },
});
