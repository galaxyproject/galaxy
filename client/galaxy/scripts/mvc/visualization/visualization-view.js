/**
 *  Visualization selection grid
 */
import * as Backbone from "backbone";
import * as _ from "underscore";
import Thumbnails from "mvc/ui/ui-thumbnails";

/* global $ */
/* global Galaxy */

var View = Backbone.View.extend({
    initialize: function(options) {
        this.setElement($("<div/>"));
        this.model = new Backbone.Model();
        this.active_tab = "visualization";
        $.ajax({
            url: `${Galaxy.root}api/datasets/${options.dataset_id}`
        }).done(dataset => {
            if (dataset.visualizations.length === 0) {
                this.$el.append(
                    $("<div/>")
                        .addClass("errormessagelarge")
                        .append(
                            $("<p/>").text(
                                "Unfortunately we could not identify a suitable plugin. Feel free to contact us if you are aware of visualizations for this datatype."
                            )
                        )
                );
            } else {
                this.model.set({ dataset: dataset });
                this.render();
            }
        });
    },

    render: function() {
        var dataset = this.model.get("dataset");
        this.vis_index = {};
        this.vis_array = [];
        _.each(
            dataset.visualizations.sort((a, b) => {
                return a.html < b.html ? -1 : 1;
            }),
            (v, id) => {
                var dict = {
                    id: id,
                    name: v.name,
                    keywords: v.keywords || [],
                    title: v.html,
                    image_src: v.logo ? Galaxy.root + v.logo : null,
                    description: v.description || "No description available.",
                    regular: v.regular,
                    visualization: v
                };
                this.vis_index[dict.id] = dict;
                this.vis_array.push(dict);
            }
        );
        this.types = new Thumbnails.View({
            title_default: "Suggested plugins",
            title_list: "List of available plugins",
            collection: this.vis_array,
            onclick: id => {
                var vis_type = this.vis_index[id];
                $("#galaxy_main").attr("src", vis_type.visualization.href);
            }
        });
        this.$el.empty().append(this.types.$el);
    }
});
export default { View: View };
