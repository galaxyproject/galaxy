/** This class renders the chart configuration form. */
import _ from "underscore";
import Backbone from "backbone";
import Utils from "utils/utils";
import { visitInputs } from "components/Form/utilities";
import FormDisplay from "components/Form/FormDisplay";
import { appendVueComponent } from "utils/mountVueComponent";

export default Backbone.View.extend({
    initialize: function (app) {
        var self = this;
        this.chart = app.chart;
        this.setElement("<div/>");
        this.listenTo(this.chart, "load", function () {
            self.render();
        });
    },
    render: function () {
        var self = this;
        var inputs = Utils.clone(this.chart.plugin.settings) || [];
        var panel_option = this.chart.plugin.specs.use_panels;
        if (panel_option == "optional") {
            inputs.push({
                name: "__use_panels",
                type: "boolean",
                label: "Use multi-panels",
                help: "Would you like to separate your data into individual panels?",
                value: false,
            });
        } else {
            this.chart.settings.set("__use_panels", panel_option == "yes" ? "true" : "false");
        }
        this.$el.empty();
        if (inputs.length > 0) {
            visitInputs(inputs, function (input, name) {
                var model_value = self.chart.settings.get(name);
                if (model_value !== undefined && !input.hidden) {
                    input.value = model_value;
                }
            });
            const instance = appendVueComponent(this.$el, FormDisplay, {
                inputs: inputs,
            });
            instance.$on("onChange", (data) => {
                this.chart.settings.set(data);
                this.chart.trigger("redraw");
            });
        }
    },
});
