/** This class renders the chart menu options. */
import Backbone from "backbone";
import Ui from "mvc/ui/ui-misc";

export default Backbone.View.extend({
    initialize: function (app) {
        this.app = app;
        this.model = new Backbone.Model({ visible: false });
        this.execute_button = new Ui.Button({
            icon: "fa-check-square",
            tooltip: "Confirm",
            onclick: () => {
                app.chart.trigger("redraw", true);
            },
        });
        this.export_button = new Ui.ButtonMenu({
            icon: "fa-camera",
            tooltip: "Export",
        });
        this.export_button.addMenu({
            key: "png",
            title: "Save as PNG",
            icon: "fa-file",
            onclick: () => {
                this._wait(app.chart, () => {
                    this.downloadAs("png");
                });
            },
        });
        this.export_button.addMenu({
            key: "svg",
            title: "Save as SVG",
            icon: "fa-file-text-o",
            onclick: () => {
                this._wait(app.chart, () => {
                    this.downloadAs("svg");
                });
            },
        });
        this.export_button.addMenu({
            key: "pdf",
            title: "Save as PDF",
            icon: "fa-file-o",
            onclick: () => {
                this._wait(app.chart, () => {
                    this.downloadAs("pdf");
                });
            },
        });
        this.left_button = new Ui.Button({
            icon: "fa-angle-double-left",
            tooltip: "Show",
            onclick: () => {
                this.model.set("visible", true);
                window.dispatchEvent(new Event("resize"));
            },
        });
        this.right_button = new Ui.Button({
            icon: "fa-angle-double-right",
            tooltip: "Hide",
            onclick: () => {
                this.model.set("visible", false);
                window.dispatchEvent(new Event("resize"));
            },
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
                        status: "success",
                    });
                    app.chart.save({
                        error: () => {
                            app.message.update({
                                message: "Could not save visualization.",
                                status: "danger",
                            });
                        },
                    });
                } else {
                    app.message.update({
                        message: "Please provide a name.",
                        status: "danger",
                    });
                }
            },
        });
        this.buttons = [this.left_button, this.right_button, this.execute_button, this.export_button, this.save_button];
        this.setElement("<div/>");
        for (const b of this.buttons) {
            this.$el.append(b.$el);
        }
        this.listenTo(this.model, "change", () => this.render());
        this.render();
    },

    downloadAs: function (filetype) {
        import(/* webpackChunkName: "Screenshot" */ "mvc/visualization/chart/components/screenshot").then(
            (Screenshot) => {
                if (filetype === "png") {
                    Screenshot.createPNG({
                        $el: this.app.viewer.$el,
                        title: this.app.chart.get("title"),
                        error: (err) => {
                            this.app.message.update({ message: err, status: "danger" });
                        },
                    });
                } else if (filetype === "svg") {
                    Screenshot.createSVG({
                        $el: this.app.viewer.$el,
                        title: this.app.chart.get("title"),
                        error: (err) => {
                            this.app.message.update({ message: err, status: "danger" });
                        },
                    });
                } else if (filetype === "pdf") {
                    Screenshot.createPDF({
                        $el: this.app.viewer.$el,
                        title: this.app.chart.get("title"),
                        error: (err) => {
                            this.app.message.update({ message: err, status: "danger" });
                        },
                    });
                } else {
                    this.app.message.update({ message: "Unknown artifact type.", status: "danger" });
                }
            }
        );
    },

    render: function () {
        var visible = this.model.get("visible");
        this.app.$el[visible ? "removeClass" : "addClass"]("charts-fullscreen");
        this.execute_button.model.set("visible", visible && !!this.app.chart.plugin.specs.confirm);
        this.save_button.model.set("visible", visible);
        this.export_button.model.set("visible", visible);
        this.right_button.model.set("visible", visible);
        this.left_button.model.set("visible", !visible);
        var exports = this.app.chart.plugin.specs.exports || [];
        this.export_button.collection.each((model) => {
            model.set("visible", exports.indexOf(model.get("key")) !== -1);
        });
    },

    _wait: function (chart, callback) {
        if (this.app.deferred.ready()) {
            callback();
        } else {
            this.app.message.update({
                message: "Your visualization is currently being processed. Please wait and try again.",
            });
        }
    },
});
