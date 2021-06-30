/**
 *  This is the primary galaxy tours definition, currently only used for
 *  rendering a tour menu.
 */
import _l from "utils/localization";
// The following must remain staged out of libs and not sourced from
// node_modules, until TDTs are bundled.
import _ from "underscore";
import $ from "jquery";
import Backbone from "backbone";
import { getAppRoot } from "onload/loadConfig";
import "@galaxyproject/bootstrap-tour";

// bootstrap-tour configures a window.Tour object; keep a local ref.
const Tour = window.Tour;

// For buttons to show, we need to add them to bootstrap/popper's sanitizing filters.
$.fn.tooltip.Constructor.Default.whiteList.button = ["data-role"];

var gxy_root = getAppRoot();

const TOURPAGE_TEMPLATE = `
    <h2>Galaxy Tours</h2>
    <p>This page presents a list of interactive tours available on this Galaxy server.
    Select any tour to get started (and remember, you can click 'End Tour' at any time).</p>

<div class="row mb-3">
    <div class="col-12 btn-group" role="group" aria-label="Tag selector">
        <% _.each(tourtagorder, function(tag) { %>
        <button class="btn btn-primary tag-selector-button" tag-selector-button="<%- tag.key %>">
            <%- tag.name %>
        </button>
        <% }); %>
    </div>
</div>

<div class="row mb-3">
    <div class="col-12">
    <h4>Tours</h4>
    <ul class="list-group">
    <% _.each(tours, function(tour) { %>
        <li class="list-group-item" tags="<%- tour.attributes.tags_lc %>">
            <a href="/tours/<%- tour.id %>" class="tourItem" data-tour.id=<%- tour.id %>>
                <%- tour.attributes.name || tour.id %>
            </a>
             - <%- tour.attributes.description || "No description given." %>
             <% _.each(tour.attributes.tags, function(tag) { %>
                <span class="badge badge-primary">
                    <%- tag.charAt(0).toUpperCase() + tag.slice(1) %>
                </span>
             <% }); %>
        </li>
    <% }); %>
    </ul>
    </div>
</div>`;

var tour_opts = {
    storage: window.sessionStorage,
    onEnd: function () {
        window.sessionStorage.removeItem("activeGalaxyTour");
    },
    delay: 150, // Attempts to make it look natural
    orphan: true,
};

var hooked_tour_from_data = (data) => {
    _.each(data.steps, (step) => {
        if (step.preclick) {
            step.onShow = () => {
                _.each(step.preclick, (preclick) => {
                    // TODO: click delay between clicks
                    $(preclick).click();
                });
            };
        }
        if (step.postclick) {
            step.onHide = () => {
                _.each(step.postclick, (postclick) => {
                    // TODO: click delay between clicks
                    $(postclick).click();
                });
            };
        }
        if (step.textinsert) {
            // Have to manually trigger a change here, for some
            // elements which have additional logic, like the
            // upload input box
            step.onShown = () => {
                $(step.element).val(step.textinsert).trigger("change");
            };
        }
        if (step.path) {
            // Galaxy does *not* support automagic path navigation right now in
            // Tours -- too many ways to get your client 'stuck' in automatic
            // navigation loops.  We can probably re-enable this as our client
            // routing matures.
            console.warn(
                "This Galaxy Tour is attempting to use path navigation.  This is known to be unstable and can possibly get the Galaxy client 'stuck' in a tour, and at this time is not allowed."
            );
            delete step.path;
        }
    });
    return data;
};

var TourItem = Backbone.Model.extend({
    urlRoot: `${gxy_root}api/tours`,
});

var Tours = Backbone.Collection.extend({
    url: `${gxy_root}api/tours`,
    model: TourItem,
});

export var ToursView = Backbone.View.extend({
    title: _l("Tours"),
    initialize: function () {
        var self = this;
        this.setElement("<div/>");
        this.model = new Tours();
        this.model.fetch({
            success: function () {
                self.render();
            },
            error: function () {
                // Do something.
                console.error("Failed to fetch tours.");
            },
        });
    },

    render: function () {
        var tpl = _.template(TOURPAGE_TEMPLATE);

        var tourtags = {};
        _.each(this.model.models, (tour) => {
            tour.attributes.tags_lc = [];
            if (tour.attributes.tags === null) {
                if (tourtags.Untagged === undefined) {
                    tourtags.Untagged = { name: "Untagged", tours: [] };
                }
                tourtags.Untagged.tours.push(tour);
            } else {
                _.each(tour.attributes.tags, (otag) => {
                    var tag = otag.charAt(0).toUpperCase() + otag.slice(1);
                    if (tourtags[tag] === undefined) {
                        tourtags[tag] = { name: tag, tours: [] };
                    }
                    tour.attributes.tags_lc.push(otag.toLowerCase());
                    tourtags[tag].tours.push(tour);
                });
            }
        });
        //var tourtagorder = Object.keys(tourtags).sort();
        var tourtagorder = [];
        Object.keys(tourtags).forEach(function (tag, index) {
            tourtagorder.push({ name: tag, key: tag.toLowerCase() });
        });

        this.$el
            .html(
                tpl({
                    tours: this.model.models,
                    tourtags: tourtags,
                    tourtagorder: tourtagorder,
                })
            )
            .on("click", ".tourItem", function (e) {
                e.preventDefault();
                giveTourById($(this).data("tour.id"));
            })
            .on("click", ".tag-selector-button", (e) => {
                var elem = $(e.target);
                var active_tags = [];

                // Switch classes for the buttons
                elem.toggleClass("btn-primary");
                elem.toggleClass("btn-secondary");

                // Get all non-disabled tags
                $(`.tag-selector-button.btn-primary`).each(function () {
                    active_tags.push($(this).attr("tag-selector-button"));
                });

                // Loop over all list items, subsequently determine these are
                // only the tours (tags should be unique). Then use the non-disabled tags to
                // determien whether or not to display this specific tour.
                $(`li.list-group-item`).each(function () {
                    if ($(this).attr("tags")) {
                        var tour_tags = [];
                        var tour_tags_html = $(this).attr("tags");

                        tour_tags = tour_tags_html.split(",");
                        var fil_tour_tags = tour_tags.filter(function (tag) {
                            return active_tags.indexOf(tag.toLowerCase()) > -1;
                        });

                        $(this).css("display", fil_tour_tags.length > 0 ? "block" : "none");
                    }
                });
            });
    },
});

export function giveTourWithData(data) {
    const hookedTourData = hooked_tour_from_data(data);
    window.sessionStorage.setItem("activeGalaxyTour", JSON.stringify(data));
    // Store tour steps in sessionStorage to easily persist w/o hackery.
    const tour = new Tour(_.extend({ steps: hookedTourData.steps }, tour_opts));
    // Always clean restart, since this is a new, explicit execution.
    tour.init();
    tour.goTo(0);
    tour.restart();
    return tour;
}

export function giveTourById(tour_id) {
    var url = `${gxy_root}api/tours/${tour_id}`;
    $.getJSON(url, (data) => {
        giveTourWithData(data);
    });
}

export function activeGalaxyTourRunner() {
    var et = JSON.parse(window.sessionStorage.getItem("activeGalaxyTour"));
    if (et) {
        et = hooked_tour_from_data(et);
        if (et && et.steps) {
            if (window && window.self === window.top) {
                // Only kick off a new tour if this is the toplevel window (non-iframe).  This
                // functionality actually *could* be useful, but we'd need to handle it better and
                // come up with some design guidelines for tours jumping between windows.
                // Disabling for now.
                var tour = new Tour(
                    _.extend(
                        {
                            steps: et.steps,
                        },
                        tour_opts
                    )
                );
                tour.init();
                tour.restart();
            }
        }
    }
}

export default {
    ToursView: ToursView,
    giveTourWithData: giveTourWithData,
    giveTourById: giveTourById,
    activeGalaxyTourRunner: activeGalaxyTourRunner,
};
