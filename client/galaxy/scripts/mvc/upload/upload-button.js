/** View for upload/progress bar button */
import $ from "jquery";
import Backbone from "backbone";
import _l from "utils/localization";

var View = Backbone.View.extend({
    initialize: function(options) {
        var self = this;
        this.model =
            (options && options.model) ||
            new Backbone.Model({
                tooltip: _l("Download from URL or upload files from disk"),
                label: "Load Data",
                percentage: 0,
                status: "",
                onunload: function() {},
                onclick: function() {}
            }).set(options);
        this.setElement(this._template());
        this.$progress = this.$(".progress-bar");
        this.listenTo(this.model, "change", this.render, this);
        this.render();
        $(window).on("beforeunload", () => self.model.get("onunload")());
    },

    render: function() {
        var options = this.model.attributes;
        this.$el
            .off("click")
            .on("click", e => {
                options.onclick(e);
            })
            .tooltip({
                title: this.model.get("tooltip"),
                placement: "bottom",
                trigger: "hover"
            });
        this.$progress
            .removeClass()
            .addClass("progress-bar")
            .addClass("progress-bar-notransition")
            .addClass(options.status != "" && `progress-bar-${options.status}`)
            .css({ width: `${options.percentage}%` });
    },

    /** Template */
    _template: function() {
        return `<div class="upload-button">
                <div class="progress">
                    <div class="progress-bar"/>
                        <a class="upload-button-link" href="javascript:void(0)" id="tool-panel-upload-button">
                            <span class="fa fa-upload"/>
                        </a>
                    </div>
            </div>`;
    }
});
export default { View: View };
