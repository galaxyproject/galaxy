/** Renders the visualization header with title, logo and description. */

import Backbone from "backbone";
import { getAppRoot } from "onload/loadConfig";
import Utils from "utils/utils";

export default Backbone.View.extend({
    initialize: function(app) {
        this.plugin = app.chart.plugin;
        this.setElement(this._template());
        this.$title = this.$(".charts-description-title");
        this.$image = this.$(".charts-description-image");
        this.$text = this.$(".charts-description-text");
        this.render();
    },
    render: function() {
        if (this.plugin.logo) {
            this.$image.attr("src", getAppRoot() + this.plugin.logo);
            this.$title.html(this.plugin.html || "Unavailable");
            this.$text.html(Utils.linkify(this.plugin.description || ""));
            this.$el.show();
        } else {
            this.$el.hide();
        }
    },
    _template: function() {
        return `<div class="charts-description">
                    <table>
                    <tr>
                        <td class="charts-description-image-td">
                            <img class="charts-description-image"/>
                        </td>
                        <td>
                            <div class="charts-description-title"/>
                        </td>
                    </tr>
                    </table>
                    <div class="charts-description-text"/>
                </div>`;
    }
});
