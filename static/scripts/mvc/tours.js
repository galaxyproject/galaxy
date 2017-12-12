define("mvc/tours", ["exports", "utils/localization", "libs/bootstrap-tour"], function(exports, _localization) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });
    exports.ToursView = undefined;
    exports.giveTourWithData = giveTourWithData;
    exports.giveTourById = giveTourById;
    exports.activeGalaxyTourRunner = activeGalaxyTourRunner;

    var _localization2 = _interopRequireDefault(_localization);

    function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : {
            default: obj
        };
    }

    var Tour = window.Tour;
    /**
     *  This is the primary galaxy tours definition, currently only used for
     *  rendering a tour menu.
     */

    // bootstrap-tour configures a window.Tour object; keep a local ref.


    var gxy_root = typeof Galaxy === "undefined" ? "/" : Galaxy.root;

    var tourpage_template = "<h2>Galaxy Tours</h2>\n<p>This page presents a list of interactive tours available on this Galaxy server.\nSelect any tour to get started (and remember, you can click 'End Tour' at any time).</p>\n\n<div class=\"col-12 btn-group\" role=\"group\" aria-label=\"Tag selector\">\n    <% _.each(tourtagorder, function(tag) { %>\n    <button class=\"btn btn-primary tag-selector-button\" tag-selector-button=\"<%- tag %>\">\n        <%- tag %>\n    </button>\n    <% }); %>\n</div>\n\n<% _.each(tourtagorder, function(tourtagkey) { %>\n<div tag=\"<%- tourtagkey %>\" style=\"display: block;\">\n    <% var tourtag = tourtags[tourtagkey]; %>\n    <h4>\n        <%- tourtag.name %>\n    </h4>\n    <ul class=\"list-group\">\n    <% _.each(tourtag.tours, function(tour) { %>\n        <li class=\"list-group-item\">\n            <a href=\"/tours/<%- tour.id %>\" class=\"tourItem\" data-tour.id=<%- tour.id %>>\n                <%- tour.name || tour.id %>\n            </a>\n             - <%- tour.attributes.description || \"No description given.\" %>\n             <% _.each(tour.attributes.tags, function(tag) { %>\n                <span class=\"label label-primary sm-label-pad\">\n                    <%- tag.charAt(0).toUpperCase() + tag.slice(1) %>\n                </span>\n             <% }); %>\n        </li>\n    <% }); %>\n    </ul>\n</div>\n<% }); %>";

    var tour_opts = {
        storage: window.sessionStorage,
        onEnd: function onEnd() {
            sessionStorage.removeItem("activeGalaxyTour");
        },
        delay: 150, // Attempts to make it look natural
        orphan: true
    };

    var hooked_tour_from_data = function hooked_tour_from_data(data) {
        _.each(data.steps, function(step) {
            if (step.preclick) {
                step.onShow = function() {
                    _.each(step.preclick, function(preclick) {
                        // TODO: click delay between clicks
                        $(preclick).click();
                    });
                };
            }
            if (step.postclick) {
                step.onHide = function() {
                    _.each(step.postclick, function(postclick) {
                        // TODO: click delay between clicks
                        $(postclick).click();
                    });
                };
            }
            if (step.textinsert) {
                // Have to manually trigger a change here, for some
                // elements which have additional logic, like the
                // upload input box
                step.onShown = function() {
                    $(step.element).val(step.textinsert).trigger("change");
                };
            }
        });
        return data;
    };

    var TourItem = Backbone.Model.extend({
        urlRoot: gxy_root + "api/tours"
    });

    var Tours = Backbone.Collection.extend({
        url: gxy_root + "api/tours",
        model: TourItem
    });

    var ToursView = exports.ToursView = Backbone.View.extend({
        title: (0, _localization2.default)("Tours"),
        initialize: function initialize() {
            var self = this;
            this.setElement("<div/>");
            this.model = new Tours();
            this.model.fetch({
                success: function success() {
                    self.render();
                },
                error: function error() {
                    // Do something.
                    console.error("Failed to fetch tours.");
                }
            });
        },

        render: function render() {
            var tpl = _.template(tourpage_template);

            var tourtags = {};
            _.each(this.model.models, function(tour) {
                if (tour.attributes.tags === null) {
                    if (tourtags.Untagged === undefined) {
                        tourtags.Untagged = {
                            name: "Untagged",
                            tours: []
                        };
                    }
                    tourtags.Untagged.tours.push(tour);
                } else {
                    _.each(tour.attributes.tags, function(tag) {
                        tag = tag.charAt(0).toUpperCase() + tag.slice(1);
                        if (tourtags[tag] === undefined) {
                            tourtags[tag] = {
                                name: tag,
                                tours: []
                            };
                        }
                        tourtags[tag].tours.push(tour);
                    });
                }
            });
            var tourtagorder = Object.keys(tourtags).sort();

            this.$el.html(tpl({
                tours: this.model.models,
                tourtags: tourtags,
                tourtagorder: tourtagorder
            })).on("click", ".tourItem", function(e) {
                e.preventDefault();
                giveTourById($(this).data("tour.id"));
            }).on("click", ".tag-selector-button", function(e) {
                var elem = $(e.target);
                var display = "block";
                var tag = elem.attr("tag-selector-button");

                elem.toggleClass("btn-primary");
                elem.toggleClass("btn-secondary");

                if (elem.hasClass("btn-secondary")) {
                    display = "none";
                }
                $("div[tag='" + tag + "']").css({
                    display: display
                });
            });
        }
    });

    function giveTourWithData(data) {
        var hookedTourData = hooked_tour_from_data(data);
        sessionStorage.setItem("activeGalaxyTour", JSON.stringify(data));
        // Store tour steps in sessionStorage to easily persist w/o hackery.
        var tour = new Tour(_.extend({
            steps: hookedTourData.steps
        }, tour_opts));
        // Always clean restart, since this is a new, explicit execution.
        tour.init();
        tour.goTo(0);
        tour.restart();
        return tour;
    }

    function giveTourById(tour_id) {
        var url = gxy_root + "api/tours/" + tour_id;
        $.getJSON(url, function(data) {
            giveTourWithData(data);
        });
    }

    function activeGalaxyTourRunner() {
        var et = JSON.parse(sessionStorage.getItem("activeGalaxyTour"));
        if (et) {
            et = hooked_tour_from_data(et);
            if (et && et.steps) {
                if (window && window.self === window.top) {
                    // Only kick off a new tour if this is the toplevel window (non-iframe).  This
                    // functionality actually *could* be useful, but we'd need to handle it better and
                    // come up with some design guidelines for tours jumping between windows.
                    // Disabling for now.
                    var tour = new Tour(_.extend({
                        steps: et.steps
                    }, tour_opts));
                    tour.init();
                    tour.restart();
                }
            }
        }
    }

    exports.default = {
        ToursView: ToursView,
        giveTourWithData: giveTourWithData,
        giveTourById: giveTourById,
        activeGalaxyTourRunner: activeGalaxyTourRunner
    };
});
//# sourceMappingURL=../../maps/mvc/tours.js.map
