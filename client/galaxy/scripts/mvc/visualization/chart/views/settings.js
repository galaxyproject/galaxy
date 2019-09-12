/** This class renders the chart configuration form. */
import _ from "underscore";
import Backbone from "backbone";
import Utils from "utils/utils";
import Form from "mvc/form/form-view";
import FormData from "mvc/form/form-data";

export default Backbone.View.extend({
    initialize: function(app, options) {
        var self = this;
        this.chart = app.chart;
        this.setElement("<div/>");
        this.listenTo(this.chart, "load", function() {
            self.render();
        });
    },
    render: function() {
        var self = this;
        var inputs = Utils.clone(this.chart.plugin.settings) || [];
        var panel_option = this.chart.plugin.specs.use_panels;
        if (panel_option == "optional") {
            inputs.push({
                name: "__use_panels",
                type: "boolean",
                label: "Use multi-panels",
                help: "Would you like to separate your data into individual panels?"
            });
        } else {
            this.chart.settings.set("__use_panels", panel_option == "yes" ? "true" : "false");
        }
        this.$el.empty();
        if (_.size(inputs) > 0) {
            FormData.visitInputs(inputs, function(input, name) {
                var model_value = self.chart.settings.get(name);
                if (model_value !== undefined && !input.hidden) {
                    input.value = model_value;
                }
            });
            this.form = new Form({
                inputs: inputs,
                onchange: function() {
                    self.chart.settings.set(self.form.data.create());
                    self.chart.trigger("redraw");
                }
            });
            this.chart.settings.set(this.form.data.create());
            this.$el.append(this.form.$el);
        }
    }
});
