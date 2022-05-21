/** This class renders the chart configuration form. */
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
        this.listenTo(this.chart, "refresh", function () {
            self.render();
        });
    },
    render: function () {
        var self = this;
        var inputs = Utils.clone(this.chart.plugin.settings) || [];
        this.$el.empty();
        if (inputs.length > 0) {
            visitInputs(inputs, function (input, name) {
                var model_value = self.chart.settings.get(name);
                if (model_value !== undefined && !input.hidden) {
                    input.value = model_value;
                } else {
                    self.chart.settings.set(name, input.value);
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
        this.chart.trigger("redraw");
    },
});
