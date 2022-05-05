import * as Toastr from "toastr";
import * as Backbone from "backbone";
import * as _ from "underscore";

/* global $ */

window.TourGenerator = Backbone.View.extend({
    initialize: function (options) {
        const Galaxy = window.bundleEntries.getGalaxyInstance();
        const toolId = options.toolId;
        const toolVersion = options.toolVersion;
        // Add attribute 'tour_id' to the execution button
        $("#execute").attr("tour_id", "execute");
        Toastr.info("Tour generation might take some time.");
        $.getJSON(
            `${Galaxy.root}api/webhooks/tour_generator/data/`, {
                tool_id: toolId,
                tool_version: toolVersion,
            },
            (obj) => {
                if (obj.success) {
                    if (obj.data.useDatasets) {
                        this._getData(obj);
                    } else {
                        this._generateTour(obj.data.tour);
                    }
                } else {
                    Toastr.warning("Cannot generate a tour.");
                    console.error("Tour Generator: " + obj.error);
                }
            }
        );
    },
    _getData: function(obj, attempts = 20, delay = 1000) {
        let datasets = [];
        _.each(obj.data.hids, (hid) => {
            Galaxy.currHistoryPanel.collection.each((dataset) => {
                datasets.push(dataset);
            }, `hid=${hid} state=ok`);
        });
        if (datasets.length === obj.data.hids.length) {
            this._generateTour(obj.data.tour);
        } else if (attempts > 0) {
            setTimeout(() => {
                this._getData(obj, attempts - 1);
            }, delay);
        } else {
            Toastr.warning("Cannot generate a tour.");
            console.error("Some of the test datasets cannot be found in the history.");
        }
    },
    _generateTour: function (data) {
        const tour = window.bundleEntries.runTour("auto.generated", data);
        // Force ending the tour when pressing the Execute button
        $("#execute").on("mousedown", () => {
            if (tour) {
                tour.end();
            }
        });
    },
});
