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
        var self = this;
        this.deferred = app.deferred;
        this.chart = app.chart;
        this.group = options.group;
        this.setElement($("<div/>"));
        this.listenTo(this.chart, "change:dataset_id", function() {
            self.render();
        });
        this.render();
    },
    render: function() {
        var self = this;
        var inputs = Utils.clone(this.chart.plugin.groups) || [];
        var dataset_id = this.chart.get("dataset_id");
        if (dataset_id) {
            this.chart.state("wait", "Loading metadata...");
            this.deferred.execute(function(process) {
                Utils.get({
                    url: getAppRoot() + "api/datasets/" + dataset_id,
                    cache: true,
                    success: function(dataset) {
                        var data_columns = {};
                        FormData.visitInputs(inputs, function(input, prefixed) {
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
                            var model_value = self.group.get(prefixed);
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
                        self.chart.state("ok", "Metadata initialized...");
                        self.form = new Form({
                            inputs: inputs,
                            onchange: function() {
                                self.group.set(self.form.data.create());
                                self.chart.set("modified", true);
                                self.chart.trigger("redraw");
                            }
                        });
                        self.group.set(self.form.data.create());
                        self.$el.empty().append(self.form.$el);
                        process.resolve();
                        self.chart.trigger("redraw");
                    }
                });
            });
        }
    }
});

export default Backbone.View.extend({
    initialize: function(app) {
        var self = this;
        this.app = app;
        this.chart = app.chart;
        this.repeat = new Repeat.View({
            title: "Data series",
            title_new: "Data series",
            min: 1,
            onnew: function() {
                self.chart.groups.add({ id: Utils.uid() });
            }
        });
        this.setElement($("<div/>").append(this.repeat.$el));
        this.listenTo(this.chart.groups, "remove", function(group) {
            self.repeat.del(group.id);
            self.chart.trigger("redraw");
        });
        this.listenTo(this.chart.groups, "reset", function() {
            self.repeat.delAll();
        });
        this.listenTo(this.chart.groups, "add", function(group) {
            self.repeat.add({
                id: group.id,
                $el: new GroupView(self.app, { group: group }).$el,
                ondel: function() {
                    self.chart.groups.remove(group);
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
