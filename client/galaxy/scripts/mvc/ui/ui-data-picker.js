/** Creates a data dialog input field */
import $ from "jquery";
import Backbone from "backbone";
import Buttons from "mvc/ui/ui-buttons";
import { getGalaxyInstance } from "app/index";

export default Backbone.View.extend({
    constructor(options) {
        const Galaxy = getGalaxyInstance();
        this.model = (options && options.model) || new Backbone.Model(options);
        this.button_dialog = new Buttons.Button({
            icon: "fa-folder-open-o",
            tooltip: "Browse Datasets",
            cls: "btn btn-secondary float-left mr-2",
            onclick: () => {
                Galaxy.data.dialog(
                    (response) => {
                        this.model.set("value", response);
                        if (this.model.get("onchange")) {
                            this.model.get("onchange")(response);
                        }
                    },
                    {
                        multiple: Boolean(this.model.get("multiple")),
                    }
                );
            },
        });
        this.$info = $("<input disabled/>").addClass("ui-input float-left");
        this.setElement($("<div/>").addClass("d-flex").append(this.button_dialog.$el).append(this.$info));
        this.listenTo(this.model, "change", this.render, this);
        this.render();
    },
    value: function (new_val) {
        if (new_val !== undefined) {
            this.model.set("value", new_val);
        }
        return this.model.get("value");
    },
    render: function () {
        this.$el.attr("id", this.model.id);
        let label = this.model.get("value");
        if (label && this.model.get("multiple")) {
            label = label.join(", ");
        }
        this.$info.val(label || "Empty");
        return this;
    },
});
