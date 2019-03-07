/** This class renders the chart menu options. */
import Backbone from "backbone";
import Ui from "mvc/ui/ui-misc";
import Screenshot from "mvc/visualization/chart/components/screenshot";

export default Backbone.View.extend({
    initialize: function(app) {
        this.app = app;
        this.model = new Backbone.Model({ visible: true });
        this.execute_button = new Ui.Button({
            icon: "fa-check-square",
            tooltip: "Confirm",
            onclick: () => {
                app.chart.trigger("redraw", true);
            }
        });
        this.export_button = new Ui.ButtonMenu({
            icon: "fa-camera",
            tooltip: "Export"
        });
        this.export_button.addMenu({
            key: "png",
            title: "Save as PNG",
            icon: "fa-file",
            onclick: () => {
                this._wait(app.chart, () => {
                    Screenshot.createPNG({
                        $el: app.viewer.$el,
                        title: app.chart.get("title"),
                        error: err => {
                            app.message.update({ message: err, status: "danger" });
                        }
                    });
                });
            }
        });
        this.export_button.addMenu({
            key: "svg",
            title: "Save as SVG",
            icon: "fa-file-text-o",
            onclick: () => {
                this._wait(app.chart, () => {
                    Screenshot.createSVG({
                        $el: app.viewer.$el,
                        title: app.chart.get("title"),
                        error: err => {
                            app.message.update({ message: err, status: "danger" });
                        }
                    });
                });
            }
        });
        this.export_button.addMenu({
            key: "pdf",
            title: "Save as PDF",
            icon: "fa-file-o",
            onclick: () => {
                app.modal.show({
                    title: "Send visualization data for PDF creation",
                    body:
                        "Galaxy does not provide integrated PDF export scripts. You may click 'Continue' to create the PDF by using a 3rd party service (https://export.highcharts.com).",
                    buttons: {
                        Cancel: () => {
                            app.modal.hide();
                        },
                        Continue: () => {
                            app.modal.hide();
                            this._wait(app.chart, () => {
                                Screenshot.createPDF({
                                    $el: app.viewer.$el,
                                    title: app.chart.get("title"),
                                    error: err => {
                                        app.message.update({ message: err, status: "danger" });
                                    }
                                });
                            });
                        }
                    }
                });
            }
        });
        this.left_button = new Ui.Button({
            icon: "fa-angle-double-left",
            tooltip: "Show",
            onclick: () => {
                this.model.set("visible", true);
                window.dispatchEvent(new Event("resize"));
            }
        });
        this.right_button = new Ui.Button({
            icon: "fa-angle-double-right",
            tooltip: "Hide",
            onclick: () => {
                this.model.set("visible", false);
                window.dispatchEvent(new Event("resize"));
            }
        });
        this.save_button = new Ui.Button({
            icon: "fa-save",
            tooltip: "Save",
            onclick: () => {
                if (app.chart.get("title")) {
                    app.message.update({
                        message: `Saving '${app.chart.get(
                            "title"
                        )}'. It will appear in the list of 'Saved Visualizations'.`,
                        status: "success"
                    });
                    app.chart.save({
                        error: () => {
                            app.message.update({
                                message: "Could not save visualization.",
                                status: "danger"
                            });
                        }
                    });
                } else {
                    app.message.update({
                        message: "Please provide a name.",
                        status: "danger"
                    });
                }
            }
        });
        this.buttons = [this.left_button, this.right_button, this.execute_button, this.export_button, this.save_button];
        this.setElement("<div/>");
        for (let b of this.buttons) {
            this.$el.append(b.$el);
        }
        this.listenTo(this.model, "change", () => this.render());
        this.render();
    },

    render: function() {
        var visible = this.model.get("visible");
        this.app.$el[visible ? "removeClass" : "addClass"]("charts-fullscreen");
        this.execute_button.model.set("visible", visible && !!this.app.chart.plugin.specs.confirm);
        this.save_button.model.set("visible", visible);
        this.export_button.model.set("visible", visible);
        this.right_button.model.set("visible", visible);
        this.left_button.model.set("visible", !visible);
        var exports = this.app.chart.plugin.specs.exports || [];
        this.export_button.collection.each(model => {
            model.set("visible", exports.indexOf(model.get("key")) !== -1);
        });
    },

    _wait: function(chart, callback) {
        if (this.app.deferred.ready()) {
            callback();
        } else {
            this.app.message.update({
                message: "Your visualization is currently being processed. Please wait and try again."
            });
        }
    }
});
