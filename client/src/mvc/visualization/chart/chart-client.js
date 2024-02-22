import { getGalaxyInstance } from "app";
import Backbone from "backbone";
import $ from "jquery";
import Modal from "mvc/ui/ui-modal";
import { getAppRoot } from "onload/loadConfig";
import Deferred from "utils/deferred";

import Chart from "./components/model";
import Editor from "./views/editor";
import Menu from "./views/menu";
import Ui from "./views/misc";
import Viewer from "./views/viewer";

/** Get boolean as string */
function asBoolean(value) {
    return String(value).toLowerCase() == "true";
}

export default Backbone.View.extend({
    initialize: function (options) {
        const Galaxy = getGalaxyInstance();
        this.modal = Galaxy && Galaxy.modal ? Galaxy.modal : new Modal.View();
        this.setElement(
            $("<div/>")
                .addClass("charts-client")
                .append($("<div/>").addClass("charts-buttons"))
                .append($("<div/>").addClass("charts-center"))
                .append($("<div/>").addClass("charts-right"))
        );
        this.$center = this.$(".charts-center");
        this.$right = this.$(".charts-right");
        this.$buttons = this.$(".charts-buttons");
        this.chart = new Chart({}, options);
        this.chart.plugin = options.visualization_plugin;
        this.chart.requiresConfirmation = asBoolean(this.chart.plugin.specs?.confirm);
        this.chart_load = options.chart_load;
        this.message = new Ui.Message();
        this.deferred = new Deferred();
        this.viewer = new Viewer(this);
        this.editor = new Editor(this);
        this.menu = new Menu(this);
        this.$center.append(this.viewer.$el);
        this.$right.append(this.message.$el).append(this.editor.$el);
        this.$buttons.append(this.menu.$el);
        $.ajax({
            url: `${getAppRoot()}api/datasets/${options.dataset_id}`,
        })
            .done((dataset) => {
                this.dataset = dataset;
                this.chart.load();
            })
            .fail((response) => {
                const message = response.responseJSON && response.responseJSON.err_msg;
                this.errormessage = message || "Import failed for unkown reason.";
            });
    },
});
