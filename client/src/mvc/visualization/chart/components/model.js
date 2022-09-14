import Backbone from "backbone";
import Utils from "utils/utils";
import { Visualization } from "mvc/visualization/visualization-model";
const MATCH_GROUP = /^groups_([0-9]+)\|([\w]+)/;

export default Backbone.Model.extend({
    defaults: {
        title: "",
        type: "",
        date: null,
        state: "",
        state_info: "",
        modified: true,
        dataset_id: "",
        dataset_id_job: null,
    },

    initialize: function (options, viz_options) {
        this.groups = new Backbone.Collection();
        this.settings = new Backbone.Model();
        this.visualization_id = viz_options.visualization_id;
        this.visualization_name = viz_options.visualization_name;
        this.dataset_id = viz_options.dataset_id;
        this.chart_dict = viz_options.chart_dict;
        console.debug("model::initialize() - Initialized with configuration:", viz_options);
    },

    reset: function () {
        this.clear().set({
            title: "New Chart",
            dataset_id: this.dataset_id,
        });
        this.settings.clear();
        this.groups.reset();
        const paramsString = window.location.search;
        const searchParams = new URLSearchParams(paramsString);
        const groups = {};
        for (const [k, v] of searchParams.entries()) {
            const matched_groups = k.match(MATCH_GROUP);
            if (matched_groups) {
                const group_id = matched_groups[1];
                const group_key = matched_groups[2];
                groups[group_id] = groups[group_id] || {};
                groups[group_id][group_key] = v;
                groups[group_id].id = group_id;
            } else {
                this.settings.set(k, v);
            }
        }
        if (Object.keys(groups).length > 0) {
            this.groups.set(Object.values(groups));
        } else {
            this.groups.add({ id: Utils.uid() });
        }
    },

    state: function (value, info) {
        this.set({ state: value, state_info: info });
        this.trigger("set:state");
        console.debug("model::state() - " + info + " (" + value + ")");
    },

    /** Create chart dictionary */
    serialize: function () {
        var d = {
            attributes: this.attributes,
            settings: this.settings.attributes,
            groups: [],
        };
        this.groups.each(function (group) {
            d.groups.push(group.attributes);
        });
        return d;
    },

    /** Pack and save nested chart model */
    save: function (options) {
        var self = this;
        options = options || {};
        this.chart_dict = this.serialize();
        var viz = new Visualization({
            id: this.visualization_id || undefined,
            type: this.visualization_name,
            title: this.get("title") || "",
            config: {
                dataset_id: this.dataset_id,
                chart_dict: this.chart_dict,
            },
        });
        viz.save()
            .then(function (response) {
                if (response && response.id) {
                    self.visualization_id = response.id;
                    if (options.success) {
                        options.success();
                    }
                    console.debug("model::save() - Received visualization id: " + response.id);
                } else {
                    if (options.error) {
                        options.error();
                    }
                    console.debug("model::save() - Unrecognized response. Saving may have failed.");
                }
            })
            .fail(function () {
                if (options.error) {
                    options.error();
                }
                console.debug("model::save() - Saving failed.");
            });
        console.debug("model::save() - Saving with configuration.");
    },

    /** Load nested models/collections from packed dictionary */
    load: function () {
        this.reset();
        var d = this.chart_dict;
        if (d && d.attributes) {
            console.debug("model::load() - Loading saved visualization.", d);
            this.set(d.attributes);
            this.state("ok", "Loading saved visualization...");
            this.settings.set(d.settings);
            this.groups.reset();
            this.groups.add(d.groups);
            this.set("modified", false);
            this.trigger("refresh");
            console.debug("model::load() - Loading chart model.");
            return true;
        } else {
            this.set("modified", true);
            this.trigger("refresh");
            console.debug("model::load() - Visualization attributes unavailable.");
            return false;
        }
    },
});
