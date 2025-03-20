/** This class renders the chart data selection form with repeats. */

import Backbone from "backbone";
import FormDisplay from "components/Form/FormDisplay";
import { visitInputs } from "components/Form/utilities";
import $ from "jquery";
import { getAppRoot } from "onload/loadConfig";
import _ from "underscore";
import { replaceChildrenWithComponent } from "utils/mountVueComponent";
import Utils from "utils/utils";

import Repeat from "./repeat";

var GroupView = Backbone.View.extend({
    initialize: function (app, options) {
        var self = this;
        this.deferred = app.deferred;
        this.chart = app.chart;
        this.group = options.group;
        this.setElement($("<div/>"));
        this.listenTo(this.chart, "change:dataset_id", function () {
            self.render();
        });
        this.render();
    },
    render: function () {
        var self = this;
        var inputs = Utils.clone(this.chart.plugin.tracks) || [];
        var dataset_id = this.chart.get("dataset_id");
        if (dataset_id) {
            this.chart.state("wait", "Loading metadata...");
            this.deferred.execute(function (process) {
                Utils.get({
                    url: getAppRoot() + "api/datasets/" + dataset_id,
                    cache: true,
                    success: function (dataset) {
                        var data_columns = {};
                        visitInputs(inputs, function (input, prefixed) {
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
                                if (columns.length > 0) {
                                    input.value = columns[0].value;
                                }
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
                            value: data_columns,
                        });
                        self.chart.state("ok", "Metadata initialized...");
                        const params = {};
                        visitInputs(inputs, (input, name) => {
                            params[name] = input.value;
                        });
                        self.redraw(params);
                        const instance = replaceChildrenWithComponent(self.el, FormDisplay, {
                            inputs: inputs,
                        });
                        instance.$on("onChange", (data) => {
                            self.redraw(data);
                        });
                        process.resolve();
                    },
                });
            });
        }
    },
    redraw(data) {
        this.group.set(data);
        this.chart.set("modified", true);
        this.chart.trigger("redraw");
    },
});

export default Backbone.View.extend({
    initialize: function (app) {
        var self = this;
        this.app = app;
        this.chart = app.chart;
        this.repeat = new Repeat.View({
            title: "Data series",
            title_new: "Data series",
            min: 1,
            onnew: function () {
                self.chart.groups.add({ id: Utils.uid() });
            },
        });
        this.setElement($("<div/>").append(this.repeat.$el));
        this.listenTo(this.chart.groups, "remove", function (group) {
            self.repeat.del(group.id);
            self.chart.trigger("redraw");
        });
        this.listenTo(this.chart.groups, "reset", function () {
            self.repeat.delAll();
        });
        this.listenTo(this.chart.groups, "add", function (group) {
            self.repeat.add({
                id: group.id,
                $el: new GroupView(self.app, { group: group }).$el,
                ondel: function () {
                    self.chart.groups.remove(group);
                },
            });
        });
    },
    render: function () {
        if (_.size(this.chart.plugin.tracks) > 0) {
            this.repeat.$el.show();
        } else {
            this.repeat.$el.hide();
        }
    },
});
