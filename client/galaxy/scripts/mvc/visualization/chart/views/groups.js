/** This class renders the chart data selection form with repeats. */

import _ from "underscore";
import $ from "jquery";
import Backbone from "backbone";
import { getAppRoot } from "onload/loadConfig";
import Utils from "utils/utils";
import Form from "mvc/form/form-view";
import Repeat from "mvc/form/form-repeat";
import FormData from "mvc/form/form-data";

var GroupView = Backbone.View.extend({
    initialize: function(app, options) {
        this.deferred = app.deferred;
        this.chart = app.chart;
        this.group = options.group;
        this.setElement($("<div/>"));
        this.listenTo(this.chart, "change:dataset_id", () => {
            this.render();
        });
        this.render();
    },
    render: function() {
        var inputs = Utils.clone(this.chart.plugin.groups) || [];
        var dataset_id = this.chart.get("dataset_id");
        if (dataset_id) {
            this.chart.state("wait", "Loading metadata...");
            this.deferred.execute(process => {
                Utils.get({
                    url: getAppRoot() + "api/datasets/" + dataset_id,
                    cache: true,
                    success: dataset => {
                        var data_columns = {};
                        FormData.visitInputs(inputs, (input, prefixed) => {
                            if (input.type == "data_column") {
                                data_columns[prefixed] = Utils.clone(input);
                                var columns = [];
                                if (input.is_auto) {
                                    columns.push({ label: "Column: Row Number", value: "auto" });
                                }
                                if (input.is_zero) {
                                    columns.push({ label: "Column: None", value: "zero" });
                                }
                                var meta = dataset.metadata_column_types;
                                for (var key in meta) {
                                    if (
                                        (["int", "float"].indexOf(meta[key]) != -1 && input.is_numeric) ||
                                        input.is_label
                                    ) {
                                        columns.push({ label: "Column: " + (parseInt(key) + 1), value: key });
                                    }
                                }
                                input.data = columns;
                            }
                            var model_value = this.group.get(prefixed);
                            if (model_value !== undefined && !input.hidden) {
                                input.value = model_value;
                            }
                        });
                        inputs.push({
                            name: "__data_columns",
                            type: "hidden",
                            hidden: true,
                            value: data_columns
                        });
                        this.chart.state("ok", "Metadata initialized...");
                        this.form = new Form({
                            inputs: inputs,
                            onchange: () => {
                                this.group.set(this.form.data.create());
                                this.chart.set("modified", true);
                                this.chart.trigger("redraw");
                            }
                        });
                        this.group.set(this.form.data.create());
                        this.$el.empty().append(this.form.$el);
                        process.resolve();
                        this.chart.trigger("redraw");
                    }
                });
            });
        }
    }
});

export default Backbone.View.extend({
    initialize: function(app) {
        this.app = app;
        this.chart = app.chart;
        this.repeat = new Repeat.View({
            title: "Data series",
            title_new: "Data series",
            min: 1,
            onnew: () => {
                this.chart.groups.add({ id: Utils.uid() });
            }
        });
        this.setElement($("<div/>").append(this.repeat.$el));
        this.listenTo(this.chart.groups, "remove", group => {
            this.repeat.del(group.id);
            this.chart.trigger("redraw");
        });
        this.listenTo(this.chart.groups, "reset", () => {
            this.repeat.delAll();
        });
        this.listenTo(this.chart.groups, "add", group => {
            this.repeat.add({
                id: group.id,
                $el: new GroupView(this.app, { group: group }).$el,
                ondel: () => {
                    this.chart.groups.remove(group);
                }
            });
        });
    },
    render: function() {
        if (_.size(this.chart.plugin.groups) > 0) {
            this.repeat.$el.show();
        } else {
            this.repeat.$el.hide();
        }
    }
});
